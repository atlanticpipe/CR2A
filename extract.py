#!/usr/bin/env python3
"""
Text extraction utility for PDF and DOCX files with OCR support.

This module provides functionality to extract clean, readable text from PDF and DOCX files
for contract analysis and API processing. It includes file validation, format-specific
extraction methods, OCR support for scanned PDFs, and graceful error handling.

Features:
- Text-based PDF extraction using pdfminer.six
- OCR for scanned/image-based PDFs using Tesseract
- DOCX text extraction using python-docx
- Automatic fallback to OCR when text extraction fails
"""

import os
import sys
from pathlib import Path
from typing import Optional, Tuple
import tempfile
import shutil

# PDF text extraction using pdfminer.six
from pdfminer.high_level import extract_text as pdf_extract_text
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from io import StringIO

# DOCX text extraction using python-docx
from docx import Document

# OCR support
try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("Warning: OCR libraries not available. Install with: pip install pytesseract pdf2image pillow")


def validate_file(file_path: str) -> bool:
    """
    Validate file exists, is readable, and has supported extension.

    Args:
        file_path: Path to the file to validate

    Returns:
        bool: True if file is valid and supported, False otherwise
    """
    if not file_path:
        print("Error: No file path provided")
        return False

    # Convert to Path object for better handling
    path = Path(file_path)

    # Check if file exists
    if not path.exists():
        print(f"Error: File '{file_path}' does not exist")
        return False

    # Check if it's actually a file (not a directory)
    if not path.is_file():
        print(f"Error: '{file_path}' is not a file")
        return False

    # Check if file is readable
    if not os.access(path, os.R_OK):
        print(f"Error: File '{file_path}' is not readable")
        return False

    # Check file extension
    supported_extensions = {'.pdf', '.docx'}
    file_extension = path.suffix.lower()

    if file_extension not in supported_extensions:
        print(f"Error: Unsupported file format '{file_extension}'. Supported formats: {', '.join(supported_extensions)}")
        return False

    return True


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text content from a PDF file using pdfminer.six.

    Args:
        file_path: Path to the PDF file

    Returns:
        str: Extracted text content from the PDF
    """
    try:
        # Use pdfminer.high_level extract_text for simplicity and reliability
        text = pdf_extract_text(file_path)

        # Clean up the extracted text
        if not text or not text.strip():
            return ""

        # Remove excessive whitespace and normalize line endings
        cleaned_text = ' '.join(text.split())

        return cleaned_text

    except Exception as e:
        print(f"Error extracting text from PDF '{file_path}': {str(e)}")
        return ""


def extract_text_from_pdf_with_ocr(file_path: str, use_ocr: bool = True) -> Tuple[str, bool]:
    """
    Extract text from PDF with automatic OCR fallback for scanned documents.
    
    This function first attempts standard text extraction. If that fails or returns
    minimal text, it automatically falls back to OCR if available.
    
    Args:
        file_path: Path to the PDF file
        use_ocr: Whether to use OCR fallback (default: True)
    
    Returns:
        Tuple[str, bool]: (extracted_text, used_ocr)
            - extracted_text: The extracted text content
            - used_ocr: True if OCR was used, False if standard extraction worked
    """
    # First try standard text extraction
    text = extract_text_from_pdf(file_path)
    
    # Check if we got meaningful text
    if text and len(text.strip()) > 100:
        # Standard extraction worked
        return text, False
    
    # Standard extraction failed or returned minimal text
    print(f"Standard extraction returned only {len(text.strip())} characters")
    
    if not use_ocr or not OCR_AVAILABLE:
        if not OCR_AVAILABLE:
            print("OCR not available. Install with: pip install pytesseract pdf2image pillow")
            print("Also install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki")
        return text, False
    
    # Try OCR extraction
    print("Attempting OCR extraction (this may take a minute)...")
    ocr_text = extract_text_with_ocr(file_path)
    
    if ocr_text and len(ocr_text.strip()) > len(text.strip()):
        print(f"✓ OCR extraction successful: {len(ocr_text.strip())} characters")
        return ocr_text, True
    
    # OCR didn't help, return original
    return text, False


def extract_text_with_ocr(file_path: str) -> str:
    """
    Extract text from a PDF using OCR (Optical Character Recognition).
    
    This function converts PDF pages to images and uses Tesseract OCR to extract text.
    Useful for scanned documents or image-based PDFs.
    
    Args:
        file_path: Path to the PDF file
    
    Returns:
        str: Extracted text from OCR
    """
    if not OCR_AVAILABLE:
        print("Error: OCR libraries not installed")
        return ""
    
    try:
        # Check if Tesseract is available
        try:
            pytesseract.get_tesseract_version()
        except Exception as e:
            print("Error: Tesseract OCR not found. Please install Tesseract:")
            print("  Windows: https://github.com/UB-Mannheim/tesseract/wiki")
            print("  Mac: brew install tesseract")
            print("  Linux: sudo apt-get install tesseract-ocr")
            return ""
        
        print(f"Converting PDF to images for OCR...")
        
        # Convert PDF to images
        # Use lower DPI for faster processing, higher for better accuracy
        images = convert_from_path(file_path, dpi=200)
        
        print(f"Processing {len(images)} pages with OCR...")
        
        # Extract text from each page
        all_text = []
        for i, image in enumerate(images, 1):
            # Show progress with percentage
            progress = (i / len(images)) * 100
            print(f"  Page {i}/{len(images)} ({progress:.0f}%)...", end='\r')
            
            # Use Tesseract to extract text
            page_text = pytesseract.image_to_string(image, lang='eng')
            
            if page_text.strip():
                all_text.append(page_text.strip())
        
        print(f"\n✓ OCR completed for {len(images)} pages" + " " * 20)  # Clear the progress line
        
        # Combine all pages
        combined_text = '\n\n'.join(all_text)
        
        # Clean up excessive whitespace
        cleaned_text = ' '.join(combined_text.split())
        
        return cleaned_text
        
    except Exception as e:
        print(f"Error during OCR extraction: {str(e)}")
        import traceback
        traceback.print_exc()
        return ""


def extract_text_from_docx(file_path: str) -> str:
    """
    Extract text content from a DOCX file using python-docx.

    Args:
        file_path: Path to the DOCX file

    Returns:
        str: Extracted text content from the DOCX
    """
    try:
        # Load the document
        doc = Document(file_path)

        # Extract text from all paragraphs
        paragraphs = [paragraph.text.strip() for paragraph in doc.paragraphs]

        # Filter out empty paragraphs and join with double newlines for readability
        text_content = '\n\n'.join([p for p in paragraphs if p])

        # Clean up excessive whitespace
        if not text_content or not text_content.strip():
            return ""

        # Normalize whitespace
        cleaned_text = ' '.join(text_content.split())

        return cleaned_text

    except Exception as e:
        print(f"Error extracting text from DOCX '{file_path}': {str(e)}")
        return ""


def extract_text(file_path: str, use_ocr: bool = True) -> str:
    """
    Main dispatcher function to extract text from PDF or DOCX files.

    This function validates the file and dispatches to the appropriate
    extraction method based on file extension. For PDFs, it automatically
    uses OCR if standard extraction fails.

    Args:
        file_path: Path to the file to extract text from
        use_ocr: Whether to use OCR fallback for PDFs (default: True)

    Returns:
        str: Extracted text content, empty string if extraction fails
    """
    # Validate file first
    if not validate_file(file_path):
        return ""

    # Determine file type and extract accordingly
    path = Path(file_path)
    file_extension = path.suffix.lower()

    if file_extension == '.pdf':
        # Use OCR-enabled extraction for PDFs
        text, used_ocr = extract_text_from_pdf_with_ocr(file_path, use_ocr)
        if used_ocr:
            print("✓ Text extracted using OCR")
        else:
            print("✓ Text extracted using standard method")
        return text
    elif file_extension == '.docx':
        return extract_text_from_docx(file_path)
    else:
        print(f"Error: Unsupported file format '{file_extension}'")
        return ""


# Example usage and testing
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python extract.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    extracted_text = extract_text(file_path)

    if extracted_text:
        print(f"Successfully extracted text from {file_path}")
        print(f"Text length: {len(extracted_text)} characters")
        # Print first 500 characters as preview
        preview = extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text
        print(f"Preview: {preview}")
    else:
        print(f"Failed to extract text from {file_path}")
        sys.exit(1)