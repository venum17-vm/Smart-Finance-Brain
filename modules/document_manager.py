"""
document_manager.py
Handles document upload and extraction
"""

import os
import fitz  # PyMuPDF
from datetime import datetime
import database as db
from modules.automation_engine import summarize_document


UPLOAD_FOLDER = "uploads"



def save_uploaded_file(uploaded_file):

    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    file_path = os.path.join(
        UPLOAD_FOLDER,
        uploaded_file.name
    )

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return file_path


def extract_pdf_text(file_path):

    text = ""

    doc = fitz.open(file_path)

    for page in doc:
        text += page.get_text()

    return text


def process_document(uploaded_file):

    try:

        file_path = save_uploaded_file(uploaded_file)

        extracted_text = extract_pdf_text(file_path)
        summary = summarize_document(extracted_text)


        db.save_document(
            uploaded_file.name,
            file_path,
            extracted_text,
            datetime.now(),
            summary
        )

        return True, {
    "text": extracted_text,
    "summary": summary
}

    except Exception as e:

        return False, str(e)