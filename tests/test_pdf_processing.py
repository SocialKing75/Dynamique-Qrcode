import pytest
import os
from backend.app.pdf_utils import add_qr_to_pdf
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from pypdf import PdfReader

def test_pdf_qr_overlay():
    # 1. Create a dummy PDF
    dummy_pdf = "test_input.pdf"
    output_pdf = "test_output.pdf"
    
    c = canvas.Canvas(dummy_pdf, pagesize=A4)
    c.drawString(100, 750, "Ceci est un document de test pour QR Code")
    c.save()
    
    # 2. Add QR configurations
    qr_configs = [
        {'content': 'https://example.com/dynamic', 'x': 450, 'y': 50, 'size': 80},
        {'content': 'https://fidealis.com/verify', 'x': 350, 'y': 50, 'size': 80}
    ]
    
    # 3. Process PDF
    add_qr_to_pdf(dummy_pdf, output_pdf, qr_configs)
    
    # 4. Verify output exists and has a page
    assert os.path.exists(output_pdf)
    reader = PdfReader(output_pdf)
    assert len(reader.pages) == 1
    
    # Cleanup
    if os.path.exists(dummy_pdf):
        os.remove(dummy_pdf)
    if os.path.exists(output_pdf):
        os.remove(output_pdf)

if __name__ == "__main__":
    test_pdf_qr_overlay()
