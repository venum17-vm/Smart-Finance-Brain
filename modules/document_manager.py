"""
document_manager.py
FIXED VERSION - No cache errors
"""

import os
from datetime import datetime
import torch
import database as db
from PIL import Image
import pytesseract
import io
import fitz

# Configure Tesseract for Windows
if os.name == 'nt':
    tesseract_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    ]
    for path in tesseract_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            break

UPLOAD_FOLDER = "uploads"

_tokenizer = None
_model = None
_model_loaded = False


def safe_download_model():
    """Download and load model safely"""
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import gc
    
    global _tokenizer, _model, _model_loaded
    
    if _model_loaded and _model is not None:
        return _tokenizer, _model
    
    model_name = "microsoft/phi-2"
    
    print("\n" + "="*60)
    print("🤖 Loading AI Model")
    print("="*60)
    
    try:
        print("📥 Loading tokenizer...")
        _tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=True
        )
        
        # Set pad token if not set
        if _tokenizer.pad_token is None:
            _tokenizer.pad_token = _tokenizer.eos_token
        
        print("✅ Tokenizer loaded!\n")
        
        gc.collect()
        
        print("📥 Loading model...")
        _model = AutoModelForCausalLM.from_pretrained(
            model_name,
            device_map="auto",
            trust_remote_code=True,
            torch_dtype=torch.float16
        )
        
        _model_loaded = True
        print("\n✅ Model ready!\n")
        
        return _tokenizer, _model
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        raise


def load_phi3_model():
    """Load model wrapper"""
    return safe_download_model()


def summarize_document(text, max_length=300):
    """
    Summarize document - FIXED version without cache errors
    """
    try:
        tokenizer, model = load_phi3_model()
        
        # Truncate text
        if len(text) > 2000:
            text = text[:2000] + "..."
        
        # Simple prompt
        prompt = f"Summarize the following text concisely:\n\n{text}\n\nSummary:"
        
        # Tokenize
        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            max_length=2048,
            truncation=True,
            padding=True
        )
        
        # Move to device
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        
        # Generate WITHOUT cache (fixes the error)
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=min(max_length, 200),
                temperature=0.7,
                top_p=0.9,
                do_sample=True,
                num_beams=1,  # Disable beam search
                use_cache=False,  # ← THIS FIXES THE ERROR
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
        
        # Decode
        result = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract summary (remove prompt)
        summary = result.replace(prompt, "").strip()
        
        # Clean up
        summary = summary.replace("Summary:", "").strip()
        
        # If summary is empty or too short, create simple summary
        if not summary or len(summary) < 20:
            words = text.split()
            summary = f"This document contains {len(words)} words about {' '.join(words[:10])}..."
        
        return summary
    
    except Exception as e:
        print(f"❌ Summarization error: {str(e)}")
        # Fallback: simple text preview
        words = text.split()[:50]
        return f"Document preview: {' '.join(words)}... ({len(text.split())} words total)"


def extract_text_from_image(uploaded_file):
    """Extract text from images using OCR"""
    try:
        image = Image.open(uploaded_file)
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Check Tesseract
        try:
            pytesseract.get_tesseract_version()
        except:
            raise Exception("Tesseract OCR not installed!")
        
        # Perform OCR
        text = pytesseract.image_to_string(image, lang='eng')
        
        # If no text found, try preprocessing
        if not text or len(text.strip()) < 5:
            try:
                import cv2
                import numpy as np
                
                img_array = np.array(image)
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                preprocessed = Image.fromarray(thresh)
                text = pytesseract.image_to_string(preprocessed, lang='eng')
            except:
                pass
        
        return text.strip()
    
    except Exception as e:
        raise Exception(f"Image extraction error: {str(e)}")


def extract_text_from_pdf(uploaded_file):
    """Extract text from PDF"""
    try:
        text = ""
        pdf = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        
        for page_num, page in enumerate(pdf, start=1):
            page_text = page.get_text()
            
            if not page_text.strip():
                try:
                    pix = page.get_pixmap(dpi=300)
                    img_data = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_data))
                    page_text = pytesseract.image_to_string(img, lang='eng')
                except:
                    page_text = ""
            
            text += f"\n--- Page {page_num} ---\n{page_text}"
        
        pdf.close()
        return text.strip()
    
    except Exception as e:
        raise Exception(f"PDF extraction error: {str(e)}")


def extract_text(uploaded_file):
    """Smart text extraction"""
    try:
        filename = uploaded_file.name
        file_ext = os.path.splitext(filename)[1].lower()
        
        uploaded_file.seek(0)
        
        if file_ext == '.pdf':
            text = extract_text_from_pdf(uploaded_file)
        elif file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
            text = extract_text_from_image(uploaded_file)
        else:
            raise Exception(f"Unsupported file: {file_ext}")
        
        if not text or len(text.strip()) < 10:
            raise Exception("No readable text found in image/document")
        
        return text
    
    except Exception as e:
        raise Exception(f"Extraction error: {str(e)}")


def save_uploaded_file(uploaded_file):
    """Save uploaded file"""
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{uploaded_file.name}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return file_path


def process_document(uploaded_file):
    """Process document: extract and summarize"""
    try:
        file_path = save_uploaded_file(uploaded_file)
        extracted_text = extract_text(uploaded_file)
        
        summary = summarize_document(extracted_text)
        
        db.save_document(
            uploaded_file.name,
            file_path,
            extracted_text,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            summary
        )
        
        return True, {
            "text": extracted_text,
            "summary": summary,
            "file_path": file_path,
            "filename": uploaded_file.name,
            "word_count": len(extracted_text.split()),
            "char_count": len(extracted_text)
        }
    
    except Exception as e:
        return False, str(e)


def extract_receipt_data(uploaded_file):
    """Extract receipt data"""
    import re
    
    try:
        raw_text = extract_text(uploaded_file)
        lines = raw_text.split('\n')
        
        receipt_data = {
            'raw_text': raw_text,
            'total': None,
            'date': None,
            'items': []
        }
        
        for line in lines:
            if 'total' in line.lower():
                amounts = re.findall(r'\d+\.?\d*', line)
                if amounts:
                    receipt_data['total'] = float(amounts[-1])
            
            date_match = re.search(r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}', line)
            if date_match:
                receipt_data['date'] = date_match.group()
            
            if re.search(r'\d+\.?\d*', line):
                receipt_data['items'].append(line.strip())
        
        return receipt_data
    
    except Exception as e:
        raise Exception(f"Receipt error: {str(e)}")


def answer_question(document_text, question):
    """Answer questions about document"""
    try:
        tokenizer, model = load_phi3_model()
        
        if len(document_text) > 1500:
            document_text = document_text[:1500] + "..."
        
        prompt = f"Document: {document_text}\n\nQuestion: {question}\n\nAnswer:"
        
        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            max_length=2048,
            truncation=True,
            padding=True
        )
        
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=150,
                temperature=0.7,
                do_sample=True,
                use_cache=False,  # ← Fix
                pad_token_id=tokenizer.pad_token_id
            )
        
        result = tokenizer.decode(outputs[0], skip_special_tokens=True)
        answer = result.replace(prompt, "").strip()
        
        return answer if answer else "Could not generate answer."
    
    except Exception as e:
        return f"Error: {str(e)}"