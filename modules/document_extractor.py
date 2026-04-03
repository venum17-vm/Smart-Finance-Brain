"""
document_extractor.py — Smart Finance Brain
Thin extraction utilities (delegates to document_manager).
"""

import os, sys

# ── Path fix: works whether this file is at root OR inside modules/ ───────────
_THIS_DIR   = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.dirname(_THIS_DIR)
for _p in [_THIS_DIR, _PARENT_DIR]:
    if _p not in sys.path:
        sys.path.insert(0, _p)
# ─────────────────────────────────────────────────────────────────────────────

from document_manager import (
    extract_text,
    extract_text_from_pdf,
    extract_text_from_image,
    extract_text_from_docx,
    extract_text_from_text_file,
)


def get_supported_formats() -> dict:
    return {
        'Documents': ['.pdf', '.docx', '.txt', '.md'],
        'Images':    ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif'],
        'Receipts':  ['.pdf', '.jpg', '.jpeg', '.png'],
    }
