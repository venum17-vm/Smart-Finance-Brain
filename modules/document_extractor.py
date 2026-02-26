import fitz  # PyMuPDF


def extract_text(uploaded_file):

    text = ""

    pdf = fitz.open(
        stream=uploaded_file.read(),
        filetype="pdf"
    )

    for page in pdf:
        text += page.get_text()

    return text