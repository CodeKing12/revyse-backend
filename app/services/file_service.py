import os
from typing import Optional
import PyPDF2
from docx import Document


class FileProcessingService:
    """Service for extracting text from various file formats."""
    
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """Extract text from a PDF file."""
        try:
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            raise Exception(f"Failed to extract text from PDF: {str(e)}")
    
    @staticmethod
    def extract_text_from_docx(file_path: str) -> str:
        """Extract text from a DOCX file."""
        try:
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            raise Exception(f"Failed to extract text from DOCX: {str(e)}")
    
    @staticmethod
    def extract_text_from_txt(file_path: str) -> str:
        """Extract text from a TXT file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except Exception as e:
            raise Exception(f"Failed to extract text from TXT: {str(e)}")
    
    @staticmethod
    def extract_text(file_path: str, file_extension: str) -> str:
        """Extract text from a file based on its extension."""
        ext = file_extension.lower().lstrip('.')
        
        if ext == 'pdf':
            return FileProcessingService.extract_text_from_pdf(file_path)
        elif ext in ['doc', 'docx']:
            return FileProcessingService.extract_text_from_docx(file_path)
        elif ext == 'txt':
            return FileProcessingService.extract_text_from_txt(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")


file_processing_service = FileProcessingService()
