"""
modules/document_manager.py — Smart Finance Brain v6.0
Image pipeline — GROQ VISION FIRST, Tesseract as fallback only.

Priority for images (.jpg .jpeg .png .bmp .tiff):
  1. Groq vision API  — reads the actual image directly, no OCR needed
  2. Tesseract OCR    — fallback if Groq key not set
  3. Error message    — tells user to set Groq key

For PDFs/DOCX/TXT: unchanged text extraction pipeline.
"""

import os
import io
import sys
import base64
from datetime import datetime

_THIS_DIR   = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.dirname(_THIS_DIR)
_ROOT       = _PARENT_DIR if os.path.basename(_THIS_DIR) == 'modules' else _THIS_DIR
for _p in [_THIS_DIR, _PARENT_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import database as db
import automation_engine as ae

# ─────────────────────────────────────────────────────────────────────────────
#  OPTIONAL IMPORTS
# ─────────────────────────────────────────────────────────────────────────────
try:
    import fitz
    PYMUPDF_OK = True
except ImportError:
    PYMUPDF_OK = False

try:
    from PIL import Image, ImageFilter, ImageEnhance, ImageOps
    PIL_OK = True
except ImportError:
    PIL_OK = False

try:
    import pytesseract
    if os.name == 'nt':
        for _tp in [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        ]:
            if os.path.exists(_tp):
                pytesseract.pytesseract.tesseract_cmd = _tp
                break
    TESSERACT_OK = True
except ImportError:
    TESSERACT_OK = False

try:
    from docx import Document as DocxDoc
    DOCX_OK = True
except ImportError:
    DOCX_OK = False

try:
    import cv2
    import numpy as np
    CV2_OK = True
except ImportError:
    CV2_OK = False

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}


# ─────────────────────────────────────────────────────────────────────────────
#  GROQ VISION — direct image reading (no OCR needed)
# ─────────────────────────────────────────────────────────────────────────────
def _extract_text_via_groq_vision(file_obj) -> str:
    """
    Send the image directly to Groq vision model.
    Returns the full extracted text — works on any bill photo, even blurry ones.
    """
    if not ae.is_configured():
        return ''
    try:
        file_obj.seek(0)
        raw    = file_obj.read()
        b64    = base64.b64encode(raw).decode('utf-8')
        name   = getattr(file_obj, 'name', 'image.jpg').lower()
        mime   = 'image/png' if name.endswith('.png') else 'image/jpeg'

        prompt = (
            "This is a financial document image — a restaurant bill, receipt, or invoice. "
            "Read ALL text visible in the image exactly as printed. "
            "List every line item with its quantity and amount. "
            "Include the total, service charge, taxes, cashier name, date, and any other details. "
            "Format the output clearly line by line, preserving the original structure. "
            "Do not skip any numbers or text."
        )
        text = ae._groq_vision(b64, mime, prompt, max_tokens=800)
        return text.strip() if text else ''
    except Exception as e:
        print(f"[Groq Vision extract] {e}")
        return ''


def _extract_financial_via_groq_vision(file_obj) -> dict:
    """
    Ask Groq vision to return structured financial data directly from the image.
    Returns dict: vendor, date, total, category, items, confidence.
    """
    if not ae.is_configured():
        return {}
    try:
        file_obj.seek(0)
        raw  = file_obj.read()
        b64  = base64.b64encode(raw).decode('utf-8')
        name = getattr(file_obj, 'name', 'image.jpg').lower()
        mime = 'image/png' if name.endswith('.png') else 'image/jpeg'

        prompt = (
            "Look at this bill/receipt image carefully. "
            "Extract the financial data and return ONLY valid JSON — no explanation, no markdown fences.\n"
            '{"vendor":"restaurant or shop name","date":"YYYY-MM-DD or null",'
            '"total":numeric_total_amount,'
            '"category":"Food & Dining|Transportation|Shopping|Entertainment|Bills & Utilities|Health|Education|Investment|Other",'
            '"items":[{"name":"item name","qty":1,"amount":0.0}],'
            '"service_charge":0.0,"taxes":0.0,"subtotal":0.0}\n'
            "Use null for any field not visible. Total must be the final payable amount as a number only."
        )
        result = ae._groq_vision(b64, mime, prompt, max_tokens=500)
        if not result:
            return {}

        import json, re
        result = re.sub(r'```json|```', '', result).strip()
        m = re.search(r'\{.*\}', result, re.DOTALL)
        if m:
            parsed = json.loads(m.group())
            parsed['confidence'] = 'high'
            return parsed
    except Exception as e:
        print(f"[Groq Vision financial] {e}")
    return {}


# ─────────────────────────────────────────────────────────────────────────────
#  TEXT EXTRACTION — per file type
# ─────────────────────────────────────────────────────────────────────────────
def extract_text_from_pdf(file_obj) -> str:
    if not PYMUPDF_OK:
        raise Exception("PyMuPDF not installed: pip install pymupdf")
    try:
        file_obj.seek(0)
        pdf  = fitz.open(stream=file_obj.read(), filetype='pdf')
        text = ''
        for i, page in enumerate(pdf, 1):
            page_text = page.get_text('text')
            if not page_text.strip():
                # Scanned PDF page — try Groq vision on the page image
                pix      = page.get_pixmap(dpi=200)
                img_data = pix.tobytes('png')
                img_io   = io.BytesIO(img_data)
                img_io.name = f'page_{i}.png'
                groq_text = _extract_text_via_groq_vision(img_io)
                if groq_text:
                    page_text = groq_text
                elif TESSERACT_OK and PIL_OK:
                    img = Image.open(io.BytesIO(img_data))
                    page_text = _ocr_financial(img)
            text += f'\n--- Page {i} ---\n{page_text}'
        pdf.close()
        return text.strip()
    except Exception as e:
        raise Exception(f"PDF error: {e}")


def extract_text_from_image(file_obj) -> str:
    """
    Image extraction — Groq vision first, Tesseract as fallback.
    """
    # ── PRIMARY: Groq vision (works on any photo, no preprocessing needed) ───
    if ae.is_configured():
        text = _extract_text_via_groq_vision(file_obj)
        if text and len(text.strip()) > 10:
            return text.strip()
        file_obj.seek(0)

    # ── FALLBACK: Tesseract OCR ───────────────────────────────────────────────
    if not TESSERACT_OK:
        raise Exception(
            "No text extracted. Either set your Groq API key in Settings "
            "or install Tesseract OCR for offline image reading."
        )
    if not PIL_OK:
        raise Exception("Pillow not installed: pip install Pillow")

    try:
        file_obj.seek(0)
        img  = Image.open(file_obj)
        text = _ocr_financial(img)

        if not text or len(text.strip()) < 15:
            text = _ocr_financial(_preprocess_financial(img))
        if not text or len(text.strip()) < 15:
            text = _ocr_financial(_enhance_for_finance(img))

        if not text or len(text.strip()) < 10:
            raise Exception(
                "Could not read text from this image. "
                "Set your Groq API key in Budget → Settings for automatic image reading."
            )
        return text.strip()
    except Exception as e:
        raise Exception(f"Image extraction error: {e}")


def extract_text_from_docx(file_obj) -> str:
    if not DOCX_OK:
        raise Exception("python-docx not installed: pip install python-docx")
    try:
        file_obj.seek(0)
        doc   = DocxDoc(file_obj)
        parts = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                row_text = ' | '.join(c.text.strip() for c in row.cells if c.text.strip())
                if row_text:
                    parts.append(row_text)
        return '\n'.join(parts).strip()
    except Exception as e:
        raise Exception(f"DOCX error: {e}")


def extract_text_from_text_file(file_obj) -> str:
    try:
        for enc in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
            try:
                file_obj.seek(0)
                return file_obj.read().decode(enc).strip()
            except (UnicodeDecodeError, AttributeError):
                continue
        return ''
    except Exception as e:
        raise Exception(f"Text file error: {e}")


def extract_text(file_obj) -> str:
    name = getattr(file_obj, 'name', 'unknown')
    ext  = os.path.splitext(name)[1].lower()
    dispatch = {
        '.pdf':  extract_text_from_pdf,
        '.jpg':  extract_text_from_image,
        '.jpeg': extract_text_from_image,
        '.png':  extract_text_from_image,
        '.bmp':  extract_text_from_image,
        '.tiff': extract_text_from_image,
        '.tif':  extract_text_from_image,
        '.webp': extract_text_from_image,
        '.docx': extract_text_from_docx,
        '.txt':  extract_text_from_text_file,
        '.md':   extract_text_from_text_file,
    }
    handler = dispatch.get(ext)
    if not handler:
        raise Exception(f"Unsupported file type: {ext}")
    return handler(file_obj)


# ─────────────────────────────────────────────────────────────────────────────
#  FULL PIPELINE
# ─────────────────────────────────────────────────────────────────────────────
def process_document(file_obj, phone: str = '') -> tuple[bool, dict | str]:
    """
    Full pipeline: save → extract → summarise → financial data → DB save.

    For images: uses Groq vision for BOTH text extraction AND financial data
    extraction in one pass — much faster and more accurate than OCR.
    """
    try:
        file_path = _save_file(file_obj, phone)
        name      = getattr(file_obj, 'name', '')
        ext       = os.path.splitext(name)[1].lower()
        is_image  = ext in IMAGE_EXTS

        # ── IMAGE: single Groq vision pass gets everything ───────────────────
        if is_image and ae.is_configured():
            file_obj.seek(0)
            fin_data = _extract_financial_via_groq_vision(file_obj)

            file_obj.seek(0)
            text     = _extract_text_via_groq_vision(file_obj)

            if not text and not fin_data:
                # Both Groq calls failed (rate limit?) — try Tesseract
                file_obj.seek(0)
                try:
                    text = extract_text_from_image(file_obj)
                except Exception:
                    text = ''

            if not text and not fin_data:
                return False, (
                    "Could not read this image. "
                    "Try: a clearer photo, better lighting, or a scanned PDF instead."
                )

            # Merge: fill any missing fin_data fields from text
            if not fin_data:
                fin_data = ae.extract_financial_data(text) if text else {}
            elif text and not fin_data.get('total'):
                fallback = ae.extract_financial_data(text)
                fin_data['total'] = fallback.get('total')

            # Build a clean summary
            summary = _build_image_summary(fin_data, text)
            doc_type = 'receipt'

        # ── PDF / DOCX / TXT: text extraction then AI analysis ───────────────
        else:
            file_obj.seek(0)
            try:
                text = extract_text(file_obj)
            except Exception as e:
                return False, str(e)

            if not text or len(text.strip()) < 10:
                return False, (
                    "Could not extract readable text from this file. "
                    "For image files, set your Groq API key in Budget → Settings."
                )

            summary  = ae.summarize_document(text)
            fin_data = ae.extract_financial_data(text)
            doc_type = _detect_doc_type(text)

        upload_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        db.save_document(
            filename    = name,
            file_path   = file_path,
            content     = text or '',
            upload_date = upload_date,
            summary     = summary,
            doc_type    = doc_type,
            phone       = phone,
        )

        return True, {
            'text':        text or '',
            'summary':     summary,
            'financial':   fin_data,
            'doc_type':    doc_type,
            'file_path':   file_path,
            'filename':    name,
            'word_count':  len((text or '').split()),
            'char_count':  len(text or ''),
            'upload_date': upload_date,
        }

    except Exception as e:
        return False, str(e)


def answer_question(document_text: str, question: str) -> str:
    return ae.answer_question(document_text, question)


# ─────────────────────────────────────────────────────────────────────────────
#  SUMMARY BUILDER FOR IMAGES
# ─────────────────────────────────────────────────────────────────────────────
def _build_image_summary(fin_data: dict, raw_text: str) -> str:
    """Build a clean human-readable summary from vision-extracted data."""
    parts = []

    vendor = fin_data.get('vendor') or fin_data.get('Vendor')
    total  = fin_data.get('total')  or fin_data.get('Total')
    date   = fin_data.get('date')   or fin_data.get('Date')
    items  = fin_data.get('items',  [])
    svc    = fin_data.get('service_charge', 0) or 0
    tax    = fin_data.get('taxes', 0) or 0
    cat    = fin_data.get('category', 'Food & Dining')

    if vendor:
        parts.append(f"Vendor: {vendor}")
    if date and date != 'null':
        parts.append(f"Date: {date}")
    if items:
        parts.append(f"{len(items)} item(s) detected")
    if svc:
        parts.append(f"Service charge: Rs.{svc:,.2f}")
    if tax:
        parts.append(f"Tax: Rs.{tax:,.2f}")
    if total:
        parts.append(f"Total amount: Rs.{float(total):,.2f}")
    if cat:
        parts.append(f"Category: {cat}")

    if parts:
        return " · ".join(parts)

    # Fallback: first 200 chars of raw text
    if raw_text:
        return raw_text[:200].replace('\n', ' ').strip()

    return "Bill/receipt processed successfully."


# ─────────────────────────────────────────────────────────────────────────────
#  IMAGE PROCESSING — Tesseract fallback helpers
# ─────────────────────────────────────────────────────────────────────────────
def _ocr_financial(img) -> str:
    if not TESSERACT_OK or not PIL_OK:
        return ''
    try:
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        w, h = img.size
        if w < 1000:
            scale = 1000 / w
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        config = '--oem 3 --psm 6 -c preserve_interword_spaces=1'
        text   = pytesseract.image_to_string(img, lang='eng', config=config)
        if len(text.strip()) < 20:
            text2 = pytesseract.image_to_string(img, lang='eng', config='--oem 3 --psm 3')
            if len(text2.strip()) > len(text.strip()):
                text = text2
        return text
    except Exception:
        try:
            return pytesseract.image_to_string(img, lang='eng')
        except Exception:
            return ''


def _preprocess_financial(img):
    if not PIL_OK:
        return img
    try:
        gray = img.convert('L')
        if CV2_OK:
            arr      = np.array(gray)
            denoised = cv2.fastNlMeansDenoising(arr, h=10, templateWindowSize=7, searchWindowSize=21)
            thresh   = cv2.adaptiveThreshold(denoised, 255,
                           cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            coords   = np.column_stack(np.where(thresh > 0))
            if len(coords) > 100:
                angle = cv2.minAreaRect(coords)[-1]
                if angle < -45:
                    angle = 90 + angle
                if abs(angle) > 0.5:
                    h, w = thresh.shape
                    M    = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
                    thresh = cv2.warpAffine(thresh, M, (w, h),
                                            flags=cv2.INTER_CUBIC,
                                            borderMode=cv2.BORDER_REPLICATE)
            return Image.fromarray(thresh)
        else:
            sharpened = gray.filter(ImageFilter.SHARPEN)
            return sharpened.point(lambda x: 0 if x < 128 else 255, '1').convert('L')
    except Exception:
        return img


def _enhance_for_finance(img):
    if not PIL_OK:
        return img
    try:
        img  = img.convert('RGB')
        img  = ImageEnhance.Contrast(img).enhance(2.5)
        img  = ImageEnhance.Sharpness(img).enhance(2.0)
        img  = ImageEnhance.Brightness(img).enhance(1.2)
        gray = img.convert('L')
        return ImageOps.autocontrast(gray, cutoff=2)
    except Exception:
        return img


# ─────────────────────────────────────────────────────────────────────────────
#  FILE SAVING
# ─────────────────────────────────────────────────────────────────────────────
def _save_file(file_obj, phone: str = '') -> str:
    upload_dir = db.get_upload_dir(phone)
    os.makedirs(upload_dir, exist_ok=True)
    ts        = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_name = ''.join(c for c in getattr(file_obj, 'name', 'file') if c.isalnum() or c in ('._-'))
    path      = os.path.join(upload_dir, f"{ts}_{safe_name}")
    file_obj.seek(0)
    with open(path, 'wb') as f:
        f.write(file_obj.read())
    return path


# ─────────────────────────────────────────────────────────────────────────────
#  DOCUMENT TYPE DETECTION
# ─────────────────────────────────────────────────────────────────────────────
def _detect_doc_type(text: str) -> str:
    t = text.lower()
    rules = [
        ('invoice',       ['invoice no', 'invoice number', 'inv#', 'bill to', 'gst invoice']),
        ('receipt',       ['receipt', 'payment received', 'thank you for', 'cash memo']),
        ('utility_bill',  ['electricity', 'water supply', 'gas bill', 'utility', 'consumer no']),
        ('bank_statement',['bank statement', 'account statement', 'closing balance', 'opening balance']),
        ('insurance',     ['insurance', 'premium', 'policy no', 'policyholder']),
        ('payslip',       ['salary', 'payslip', 'payroll', 'ctc', 'basic pay', 'net pay']),
        ('tax',           ['income tax', 'form 16', 'tds certificate', 'gst return']),
        ('loan',          ['emi', 'loan statement', 'principal', 'interest', 'outstanding loan']),
    ]
    for doc_type, keywords in rules:
        if any(kw in t for kw in keywords):
            return doc_type
    return 'general'
