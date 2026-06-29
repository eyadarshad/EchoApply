import fitz  # PyMuPDF
import os
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class PDFParserError(Exception):
    """Base exception for PDF parsing errors."""
    pass

class ScannedPDFError(PDFParserError):
    """Raised when a PDF is scanned/image-only and cannot be read without OCR."""
    pass

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extracts plain text from PDF bytes.
    If no text layer is detected, it falls back to OCR.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        raise PDFParserError(f"Failed to parse PDF document structure: {str(e)}")

    if len(doc) == 0:
        raise PDFParserError("The uploaded PDF has 0 pages.")

    full_text = []
    has_text_layer = False

    for page in doc:
        text = page.get_text()
        if text.strip():
            has_text_layer = True
        full_text.append(text)

    extracted_text = "\n".join(full_text).strip()
    logger.debug(f"[DEBUG PyMuPDF] Extracted raw text length: {len(extracted_text)} chars. First 500 chars:\n{extracted_text[:500]}")

    # Detect scanned / empty text layer
    if not has_text_layer or len(extracted_text) < 100:
        logger.info("Minimal text layer found. Invoking OCR fallback...")
        ocr_text = run_ocr_fallback(doc)
        if ocr_text.strip():
            ocr_text_clean = ocr_text.strip()
            logger.debug(f"[DEBUG OCR] Extracted OCR text length: {len(ocr_text_clean)} chars. First 500 chars:\n{ocr_text_clean[:500]}")
            return ocr_text_clean
        else:
            raise ScannedPDFError(
                "This PDF appears to be scanned or image-only, and OCR could not extract any text. "
                "Please upload a PDF containing a selectable text layer."
            )

    return extracted_text

def run_ocr_fallback(doc: fitz.Document) -> str:
    """
    Renders PDF pages to images and runs Tesseract OCR.
    """
    try:
        import pytesseract
        from PIL import Image
        import io
    except ImportError:
        logger.warning("OCR libraries (pytesseract/pillow) not available. Skipping OCR.")
        return ""

    ocr_pages = []
    for page_num in range(len(doc)):
        try:
            page = doc[page_num]
            # Render page to image
            pix = page.get_pixmap(dpi=150)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # Run OCR
            text = pytesseract.image_to_string(img)
            ocr_pages.append(text)
        except Exception as e:
            logger.error(f"OCR failed on page {page_num}: {str(e)}")
            # If tesseract binary is not installed, it raises pytesseract.TesseractNotFoundError
            continue

    return "\n".join(ocr_pages)

def extract_blocks_from_pdf(pdf_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Extracts text blocks with layout coordinates to assist the LLM
    in reconstructing multi-column or complex layouts.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        raise PDFParserError(f"Failed to parse PDF document structure: {str(e)}")

    blocks_data = []
    for page_num, page in enumerate(doc):
        # get_text("blocks") returns a list of tuples:
        # (x0, y0, x1, y1, "text", block_no, block_type)
        blocks = page.get_text("blocks")
        for b in blocks:
            # block_type 0 means text
            if b[6] == 0:
                blocks_data.append({
                    "page": page_num + 1,
                    "x0": round(b[0], 2),
                    "y0": round(b[1], 2),
                    "x1": round(b[2], 2),
                    "y1": round(b[3], 2),
                    "text": b[4].strip(),
                    "block_no": b[5]
                })
    return blocks_data

def render_pdf_to_images(pdf_bytes: bytes) -> List[Any]:
    """
    Renders PDF pages to PIL Images.
    """
    import io
    from PIL import Image
    
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    for page in doc:
        pix = page.get_pixmap(dpi=150)
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        images.append(img)
    return images
