"""
File Extraction Service
Provides clean, accurate text extraction from various file formats.
"""

import logging
from typing import Optional, BinaryIO
from io import BytesIO

logger = logging.getLogger(__name__)


def extract_text_file(file: BinaryIO, filename: str) -> str:
    """
    Extract text from plain text files (.txt, .md)
    
    Args:
        file: File object to extract from
        filename: Name of the file (for logging)
        
    Returns:
        Extracted text content
        
    Raises:
        ValueError: If file cannot be decoded as UTF-8
    """
    try:
        content = file.read().decode('utf-8')
        logger.info(f"Successfully extracted text from {filename}: {len(content)} characters")
        return content
    except UnicodeDecodeError as e:
        logger.error(f"Failed to decode {filename} as UTF-8: {e}")
        raise ValueError(f"File {filename} is not a valid UTF-8 text file")


def extract_pdf_file(file: BinaryIO, filename: str) -> str:
    """
    Extract text from PDF files using PyPDF2
    
    Args:
        file: File object to extract from
        filename: Name of the file (for logging)
        
    Returns:
        Extracted text content from all pages
        
    Raises:
        ImportError: If PyPDF2 is not installed
        ValueError: If PDF cannot be read or parsed
    """
    try:
        import PyPDF2
    except ImportError:
        logger.error("PyPDF2 not installed. Cannot extract PDF content.")
        raise ImportError("PyPDF2 library is required for PDF extraction. Please install it with: pip install PyPDF2")
    
    try:
        # Read the file into a BytesIO object for PyPDF2
        file.seek(0)
        pdf_bytes = BytesIO(file.read())
        
        # Create PDF reader
        pdf_reader = PyPDF2.PdfReader(pdf_bytes)
        
        # Extract text from all pages
        extracted_text = []
        for page_num, page in enumerate(pdf_reader.pages, start=1):
            try:
                page_text = page.extract_text()
                if page_text.strip():  # Only add non-empty pages
                    extracted_text.append(f"--- Page {page_num} ---\n{page_text}")
            except Exception as e:
                logger.warning(f"Error extracting text from page {page_num} of {filename}: {e}")
                continue
        
        if not extracted_text:
            logger.warning(f"No text could be extracted from PDF: {filename}")
            return f"[PDF file '{filename}' appears to be empty or contains only images]"
        
        content = "\n\n".join(extracted_text)
        logger.info(f"Successfully extracted text from PDF {filename}: {len(content)} characters from {len(extracted_text)} pages")
        return content
        
    except Exception as e:
        logger.error(f"Failed to extract PDF content from {filename}: {e}")
        raise ValueError(f"Unable to extract content from PDF file: {str(e)}")


def extract_docx_file(file: BinaryIO, filename: str) -> str:
    """
    Extract text from DOCX files using python-docx
    
    Args:
        file: File object to extract from
        filename: Name of the file (for logging)
        
    Returns:
        Extracted text content from all paragraphs
        
    Raises:
        ImportError: If python-docx is not installed
        ValueError: If DOCX cannot be read or parsed
    """
    try:
        from docx import Document
    except ImportError:
        logger.error("python-docx not installed. Cannot extract DOCX content.")
        raise ImportError("python-docx library is required for DOCX extraction. Please install it with: pip install python-docx")
    
    try:
        # Read the file into a BytesIO object for python-docx
        file.seek(0)
        docx_bytes = BytesIO(file.read())
        
        # Create Document object
        doc = Document(docx_bytes)
        
        # Extract text from all paragraphs
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        
        if not paragraphs:
            logger.warning(f"No text could be extracted from DOCX: {filename}")
            return f"[DOCX file '{filename}' appears to be empty]"
        
        content = "\n\n".join(paragraphs)
        logger.info(f"Successfully extracted text from DOCX {filename}: {len(content)} characters from {len(paragraphs)} paragraphs")
        return content
        
    except Exception as e:
        logger.error(f"Failed to extract DOCX content from {filename}: {e}")
        raise ValueError(f"Unable to extract content from DOCX file: {str(e)}")


def extract_doc_file(file: BinaryIO, filename: str) -> str:
    """
    Extract text from legacy DOC files
    
    Note: Legacy .doc files are in a proprietary binary format that requires
    specialized libraries. For production use, consider using LibreOffice or
    converting to DOCX first.
    
    Args:
        file: File object to extract from
        filename: Name of the file (for logging)
        
    Returns:
        Error message indicating DOC files are not supported
        
    Raises:
        ValueError: Always, as DOC format requires additional dependencies
    """
    logger.warning(f"Legacy .doc file format not supported: {filename}")
    raise ValueError(
        "Legacy .doc files are not supported. Please convert to .docx format or use .txt, .md, or .pdf files instead."
    )


def extract_file_content(file: BinaryIO, filename: str) -> str:
    """
    Extract text content from uploaded file based on file extension
    
    Supported formats:
    - .txt, .md: Plain text files
    - .pdf: PDF documents
    - .docx: Microsoft Word documents (modern format)
    
    Args:
        file: File object to extract from
        filename: Name of the file (used to determine type)
        
    Returns:
        Extracted text content
        
    Raises:
        ValueError: If file type is unsupported or extraction fails
    """
    # Get file extension
    file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
    
    # Route to appropriate extraction function
    if file_ext in ['txt', 'md']:
        return extract_text_file(file, filename)
    
    elif file_ext == 'pdf':
        return extract_pdf_file(file, filename)
    
    elif file_ext == 'docx':
        return extract_docx_file(file, filename)
    
    elif file_ext == 'doc':
        return extract_doc_file(file, filename)
    
    else:
        logger.error(f"Unsupported file type: {filename} (extension: {file_ext})")
        raise ValueError(
            f"Unsupported file type: '.{file_ext}'. "
            f"Supported formats: .txt, .md, .pdf, .docx"
        )


def format_file_content_for_prompt(original_prompt: str, filename: str, file_content: str) -> str:
    """
    Format the extracted file content into a well-structured prompt
    
    Args:
        original_prompt: User's original prompt/query
        filename: Name of the attached file
        file_content: Extracted content from the file
        
    Returns:
        Formatted prompt combining user query and file content
    """
    formatted_prompt = f"""{original_prompt}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📎 ATTACHED FILE: {filename}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{file_content}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Please respond to my request above, taking into account the content from the attached file."""
    
    return formatted_prompt


# Service instance for easy import
class FileExtractionService:
    """Service class for file extraction operations"""
    
    @staticmethod
    def extract_content(file: BinaryIO, filename: str) -> str:
        """Extract content from file"""
        return extract_file_content(file, filename)
    
    @staticmethod
    def format_for_prompt(original_prompt: str, filename: str, file_content: str) -> str:
        """Format extracted content for AI prompt"""
        return format_file_content_for_prompt(original_prompt, filename, file_content)


# Global service instance
file_extraction_service = FileExtractionService()
