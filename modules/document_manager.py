"""
modules/document_manager.py — Smart Finance Brain v5.0
Enhanced OCR pipeline tuned for financial documents:
  - Multi-pass OCR with preprocessing
  - DPI 300 for receipts, 200 for standard docs
  - Deskew + denoise + contrast for bills and receipts
  - Per-user upload folder: uploads/{phone}/
"""

import os
import io
import sys
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
        for tp in [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        ]:
            if os.path.exists(tp):
                pytesseract.pytesseract.tesseract_cmd = tp
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


# ─────────────────────────────────────────────────────────────────────────────
#  TEXT EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────
def extract_text_from_pdf(file_obj) -> str:
    if not PYMUPDF_OK:
        raise Exception("PyMuPDF not installed: pip install pymupdf")
    try:
        file_obj.seek(0)
        pdf  = fitz.open(stream=file_obj.read(), filetype="pdf")
        text = ""
        for i, page in enumerate(pdf, 1):
            page_text = page.get_text("text")
            if not page_text.strip() and TESSERACT_OK and PIL_OK:
                # Scanned page — use high DPI for OCR
                pix      = page.get_pixmap(dpi=300)
                img_data = pix.tobytes("png")
                img      = Image.open(io.BytesIO(img_data))
                page_text = _ocr_financial(img)
            text += f"\n--- Page {i} ---\n{page_text}"
        pdf.close()
        return text.strip()
    except Exception as e:
        raise Exception(f"PDF error: {e}")


def extract_text_from_image(file_obj) -> str:
    """
    Multi-pass OCR for financial images (bills, receipts, invoices).
    Tries raw → preprocessed → enhanced to get best result.
    """
    if not TESSERACT_OK:
        raise Exception("pytesseract not installed: pip install pytesseract")
    if not PIL_OK:
        raise Exception("Pillow not installed: pip install Pillow")
    try:
        file_obj.seek(0)
        img = Image.open(file_obj)

        # Pass 1: raw image
        text = _ocr_financial(img)

        # Pass 2: preprocessed if result is poor
        if not text or len(text.strip()) < 15:
            preprocessed = _preprocess_financial(img)
            text = _ocr_financial(preprocessed)

        # Pass 3: enhanced contrast + sharpness
        if not text or len(text.strip()) < 15:
            enhanced = _enhance_for_finance(img)
            text = _ocr_financial(enhanced)

        return text.strip()
    except Exception as e:
        raise Exception(f"Image OCR error: {e}")


def extract_text_from_docx(file_obj) -> str:
    if not DOCX_OK:
        raise Exception("python-docx not installed: pip install python-docx")
    try:
        file_obj.seek(0)
        doc = DocxDoc(file_obj)
        parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                parts.append(para.text)
        # Also extract tables
        for table in doc.tables:
            for row in table.rows:
                row_text = ' | '.join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    parts.append(row_text)
        return '\n'.join(parts).strip()
    except Exception as e:
        raise Exception(f"DOCX error: {e}")


def extract_text_from_text_file(file_obj) -> str:
    try:
        file_obj.seek(0)
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
    Full pipeline: save → extract → summarise → financial extract → DB save
    Files go to uploads/{phone}/
    """
    try:
        file_path = _save_file(file_obj, phone)
        file_obj.seek(0)
        text = extract_text(file_obj)
        if not text or len(text.strip()) < 10:
            return False, "Could not extract readable text from this file."

        summary  = ae.summarize_document(text)
        fin_data = ae.extract_financial_data(text)
        doc_type = _detect_doc_type(text)

        upload_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        db.save_document(
            filename    = file_obj.name,
            file_path   = file_path,
            content     = text,
            upload_date = upload_date,
            summary     = summary,
            doc_type    = doc_type,
            phone       = phone,
        )

        return True, {
            'text':       text,
            'summary':    summary,
            'financial':  fin_data,
            'doc_type':   doc_type,
            'file_path':  file_path,
            'filename':   file_obj.name,
            'word_count': len(text.split()),
            'char_count': len(text),
            'upload_date':upload_date,
        }

    except Exception as e:
        return False, str(e)


def answer_question(document_text: str, question: str) -> str:
    return ae.answer_question(document_text, question)


# ─────────────────────────────────────────────────────────────────────────────
#  IMAGE PROCESSING — FINANCE-TUNED
# ─────────────────────────────────────────────────────────────────────────────
def _ocr_financial(img) -> str:
    """Run Tesseract with finance-optimised config."""
    if not TESSERACT_OK or not PIL_OK:
        return ''
    try:
        # Ensure RGB
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')

        # Resize to optimal OCR size — Tesseract works best at 300 DPI equivalent
        w, h = img.size
        if w < 1000:
            scale = 1000 / w
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

        # Config: PSM 6 = single block of text (good for bills); OEM 3 = LSTM
        config = '--oem 3 --psm 6 -c preserve_interword_spaces=1'
        text   = pytesseract.image_to_string(img, lang='eng', config=config)

        # If result is sparse, try PSM 3 (auto-detect layout)
        if len(text.strip()) < 20:
            config2 = '--oem 3 --psm 3'
            text2   = pytesseract.image_to_string(img, lang='eng', config=config2)
            if len(text2.strip()) > len(text.strip()):
                text = text2

        return text
    except Exception:
        try:
            return pytesseract.image_to_string(img, lang='eng')
        except Exception:
            return ''


def _preprocess_financial(img) -> 'Image':
    """
    Preprocessing pipeline for financial documents:
    grayscale → denoise → adaptive threshold → deskew.
    """
    if not PIL_OK:
        return img
    try:
        # Convert to grayscale
        gray = img.convert('L')

        if CV2_OK:
            arr = np.array(gray)

            # Denoise
            denoised = cv2.fastNlMeansDenoising(arr, h=10, templateWindowSize=7, searchWindowSize=21)

            # Adaptive threshold — handles uneven lighting in photos of receipts
            thresh = cv2.adaptiveThreshold(
                denoised, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )

            # Deskew (straighten tilted photos)
            coords  = np.column_stack(np.where(thresh > 0))
            if len(coords) > 100:
                angle  = cv2.minAreaRect(coords)[-1]
                if angle < -45:
                    angle = 90 + angle
                if abs(angle) > 0.5:
                    (h, w) = thresh.shape
                    M    = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
                    thresh = cv2.warpAffine(thresh, M, (w, h),
                                            flags=cv2.INTER_CUBIC,
                                            borderMode=cv2.BORDER_REPLICATE)

            return Image.fromarray(thresh)

        else:
            # PIL-only fallback: sharpen + threshold
            sharpened = gray.filter(ImageFilter.SHARPEN)
            return sharpened.point(lambda x: 0 if x < 128 else 255, '1').convert('L')

    except Exception:
        return img


def _enhance_for_finance(img) -> 'Image':
    """Boost contrast and sharpness — helps with faded receipts and thermal prints."""
    if not PIL_OK:
        return img
    try:
        img = img.convert('RGB')
        img = ImageEnhance.Contrast(img).enhance(2.5)
        img = ImageEnhance.Sharpness(img).enhance(2.0)
        img = ImageEnhance.Brightness(img).enhance(1.2)
        gray = img.convert('L')
        return ImageOps.autocontrast(gray, cutoff=2)
    except Exception:
        return img


# ─────────────────────────────────────────────────────────────────────────────
#  FILE SAVING  (per-user uploads/)
# ─────────────────────────────────────────────────────────────────────────────
def _save_file(file_obj, phone: str = '') -> str:
    """Save file to uploads/{phone}/ and return the path."""
    upload_dir = db.get_upload_dir(phone)
    os.makedirs(upload_dir, exist_ok=True)
    ts        = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c for c in file_obj.name if c.isalnum() or c in ('._-'))
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
        ('invoice',      ['invoice no', 'invoice number', 'inv#', 'bill to', 'gst invoice']),
        ('receipt',      ['receipt', 'payment received', 'thank you for', 'cash memo']),
        ('utility_bill', ['electricity', 'water supply', 'gas bill', 'utility', 'consumer no']),
        ('bank_statement',['bank statement', 'account statement', 'closing balance', 'opening balance']),
        ('insurance',    ['insurance', 'premium', 'policy no', 'policyholder']),
        ('payslip',      ['salary', 'payslip', 'payroll', 'ctc', 'basic pay', 'net pay']),
        ('tax',          ['income tax', 'form 16', 'tds certificate', 'gst return']),
        ('loan',         ['emi', 'loan statement', 'principal', 'interest', 'outstanding loan']),
    ]
    for doc_type, keywords in rules:
        if any(kw in t for kw in keywords):
            return doc_type
    return 'general'
