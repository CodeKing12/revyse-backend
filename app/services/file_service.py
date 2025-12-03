import os
from typing import Optional
import base64
from app.core.config import settings


class FileProcessingService:
    """Service for extracting text from various file formats using ONLY AI (no traditional libraries)."""
    
    def __init__(self):
        # Import here to avoid circular dependency
        from app.services.ai_service import ai_service
        self.ai_service = ai_service
    
    @staticmethod
    def _read_file_as_base64(file_path: str) -> str:
        """Read file and encode as base64."""
        with open(file_path, 'rb') as file:
            return base64.b64encode(file.read()).decode('utf-8')
    
    @staticmethod
    def extract_text_from_txt(file_path: str) -> str:
        """Extract text from a TXT file (no AI needed for plain text)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except Exception as e:
            raise Exception(f"Failed to extract text from TXT: {str(e)}")
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from a PDF file using ONLY AI (no PyPDF2 or other libraries)."""
        if not self.ai_service:
            raise Exception("AI service is not configured. Please set OPENROUTER_API_KEY.")
        
        try:
            # Use pure AI to extract text from PDF
            return self.ai_service.extract_text_from_document(file_path, "pdf")
        except Exception as e:
            raise Exception(f"Failed to extract text from PDF using AI: {str(e)}")
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from a DOCX file using ONLY AI (no python-docx or other libraries)."""
        if not self.ai_service:
            raise Exception("AI service is not configured. Please set OPENROUTER_API_KEY.")
        
        try:
            # Use pure AI to extract text from DOCX
            return self.ai_service.extract_text_from_document(file_path, "docx")
        except Exception as e:
            raise Exception(f"Failed to extract text from DOCX using AI: {str(e)}")
    
    def extract_text(self, file_path: str, file_extension: str) -> str:
        """Extract text from a file based on its extension. Uses ONLY AI for PDF/DOCX."""
        ext = file_extension.lower().lstrip('.')
        
        if ext == 'pdf':
            return self.extract_text_from_pdf(file_path)
        elif ext in ['doc', 'docx']:
            return self.extract_text_from_docx(file_path)
        elif ext == 'txt':
            return self.extract_text_from_txt(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")


file_processing_service = FileProcessingService()
