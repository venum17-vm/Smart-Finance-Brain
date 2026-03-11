"""
Enhanced text extraction supporting multiple file formats:
- PDF files
- Images (JPG, PNG, JPEG)
- Scanned receipts and bills (OCR)
- Text files
- Word documents
"""

import fitz  # PyMuPDF
from PIL import Image
import pytesseract
import io
import os


def extract_text_from_pdf(uploaded_file):
    """
    Extract text from PDF files
    """
    try:
        text = ""
        pdf = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        
        for page_num, page in enumerate(pdf, start=1):
            page_text = page.get_text()
            
            # If page has no text, it might be scanned - try OCR
            if not page_text.strip():
                # Convert PDF page to image and use OCR
                pix = page.get_pixmap()
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                page_text = pytesseract.image_to_string(img)
            
            text += f"\n--- Page {page_num} ---\n"
            text += page_text
        
        pdf.close()
        return text.strip()
    
    except Exception as e:
        raise Exception(f"Error extracting PDF: {str(e)}")


def extract_text_from_image(uploaded_file):
    """
    Extract text from images using OCR (Tesseract)
    Works for: JPG, PNG, JPEG, receipts, bills, handwritten notes
    """
    try:
        # Open image
        image = Image.open(uploaded_file)
        
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Perform OCR
        text = pytesseract.image_to_string(image)
        
        return text.strip()
    
    except Exception as e:
        raise Exception(f"Error extracting from image: {str(e)}")


def extract_text_from_text_file(uploaded_file):
    """
    Extract text from plain text files (.txt, .md)
    """
    try:
        text = uploaded_file.read().decode('utf-8')
        return text.strip()
    except UnicodeDecodeError:
        # Try with different encoding
        uploaded_file.seek(0)
        text = uploaded_file.read().decode('latin-1')
        return text.strip()


def extract_text_from_docx(uploaded_file):
    """
    Extract text from Word documents (.docx)
    """
    try:
        from docx import Document
        
        doc = Document(uploaded_file)
        text = ""
        
        for para in doc.paragraphs:
            text += para.text + "\n"
        
        return text.strip()
    
    except ImportError:
        raise Exception("python-docx not installed. Run: pip install python-docx")
    except Exception as e:
        raise Exception(f"Error extracting from Word document: {str(e)}")


def extract_text(uploaded_file):
    """
    Smart text extraction - automatically detects file type and extracts text
    
    Supported formats:
    - PDF files (.pdf)
    - Images (.jpg, .jpeg, .png, .bmp, .tiff) - uses OCR
    - Text files (.txt, .md)
    - Word documents (.docx)
    
    Args:
        uploaded_file: Streamlit uploaded file object
    
    Returns:
        Extracted text as string
    """
    try:
        # Get file extension
        filename = uploaded_file.name
        file_ext = os.path.splitext(filename)[1].lower()
        
        # Reset file pointer
        uploaded_file.seek(0)
        
        # Route to appropriate extractor based on file type
        if file_ext == '.pdf':
            return extract_text_from_pdf(uploaded_file)
        
        elif file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']:
            return extract_text_from_image(uploaded_file)
        
        elif file_ext in ['.txt', '.md']:
            return extract_text_from_text_file(uploaded_file)
        
        elif file_ext == '.docx':
            return extract_text_from_docx(uploaded_file)
        
        else:
            raise Exception(f"Unsupported file type: {file_ext}")
    
    except Exception as e:
        raise Exception(f"Error extracting text: {str(e)}")


def extract_text_from_receipt(uploaded_file):
    """
    Specialized function for receipt/bill extraction
    Optimized for structured data extraction
    
    Returns:
        Dictionary with structured data
    """
    try:
        # Extract raw text
        raw_text = extract_text(uploaded_file)
        
        # Parse receipt data
        lines = raw_text.split('\n')
        
        # Try to find key information
        receipt_data = {
            'raw_text': raw_text,
            'items': [],
            'total': None,
            'date': None,
            'merchant': None
        }
        
        # Simple parsing logic (customize based on your receipt format)
        import re
        
        for line in lines:
            # Look for total amount
            if 'total' in line.lower():
                # Extract numbers
                amounts = re.findall(r'\d+\.?\d*', line)
                if amounts:
                    receipt_data['total'] = float(amounts[-1])
            
            # Look for date patterns
            date_pattern = r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}'
            dates = re.findall(date_pattern, line)
            if dates:
                receipt_data['date'] = dates[0]
            
            # Look for amounts in line (potential items)
            if re.search(r'\d+\.?\d*', line) and not any(kw in line.lower() for kw in ['total', 'tax', 'subtotal']):
                receipt_data['items'].append(line.strip())
        
        return receipt_data
    
    except Exception as e:
        raise Exception(f"Error parsing receipt: {str(e)}")


def get_supported_formats():
    """
    Return list of supported file formats
    """
    return {
        'Documents': ['.pdf', '.docx', '.txt', '.md'],
        'Images': ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif'],
        'Receipts/Bills': ['.pdf', '.jpg', '.jpeg', '.png']
    }


def preprocess_image_for_ocr(image):
    """
    Preprocess image to improve OCR accuracy
    """
    import cv2
    import numpy as np
    
    # Convert PIL Image to numpy array
    img_array = np.array(image)
    
    # Convert to grayscale
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    
    # Apply thresholding to get better contrast
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Denoise
    denoised = cv2.fastNlMeansDenoising(thresh)
    
    # Convert back to PIL Image
    processed_image = Image.fromarray(denoised)
    
    return processed_image