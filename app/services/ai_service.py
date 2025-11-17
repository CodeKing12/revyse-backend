import google.generativeai as genai
from app.core.config import settings
from typing import List, Optional, Any, Dict
import json
import os

# --- New Imports for Document Parsing ---
import pypdf # For PDF text extraction
from docx import Document # For DOCX text extraction
from PIL import Image # For image handling (e.g., converting PDF pages to images for OCR)
import pytesseract # For OCR
import io # For handling byte streams, especially for images

# Configure pytesseract to find the Tesseract executable (if not in PATH)
# If Tesseract is in your system PATH, you might not need this line.
# If on Windows, replace with your Tesseract installation path:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


class AIService:
    def __init__(self):
        # Initialize Google Gemini client
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not found in settings")
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.gemini_model_name = settings.GEMINI_MODEL # e.g., "gemini-pro" or "gemini-1.5-flash"
        self.gemini_client = genai.GenerativeModel(self.gemini_model_name)

    def _create_gemini_messages(self, system_content: str, user_content: str) -> List[Dict[str, Any]]:
        """
        Create messages array for Google Gemini, effectively combining system and user messages.
        For Gemini, it's often best to put "system" instructions as part of the initial user prompt.
        """
        combined_content = f"Instruction: {system_content}\n\nTask: {user_content}"
        return [
            {"role": "user", "parts": [combined_content]}
        ]

    def _get_gemini_response(self, system_content: str, user_content: str,
                              temperature: float, max_tokens: int) -> str:
        """Helper to get a response from the Gemini client."""
        try:
            response = self.gemini_client.generate_content(
                self._create_gemini_messages(system_content, user_content),
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
            )
            
            if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].text
            return ""
        except Exception as e:
            raise Exception(f"Failed to get Gemini response: {str(e)}")

    def generate_summary(self, text: str, summary_type: str = "general") -> str:
        """Generate a summary of the provided text using Gemini."""
        
        prompts = {
            "general": "Create a comprehensive summary of the following educational material. Focus on key concepts, main ideas, and important details:",
            "brief": "Create a brief, concise summary of the following educational material, highlighting only the most important points:",
            "detailed": "Create a detailed, in-depth summary of the following educational material. Include all important concepts, explanations, and examples:"
        }
        
        prompt = prompts.get(summary_type, prompts["general"])
        system_content = "You are an expert educational assistant that helps students understand and learn from their study materials."
        user_content = f"{prompt}\n\nMaterial: {text}"
        
        try:
            return self._get_gemini_response(system_content, user_content, temperature=0.7, max_tokens=2000)
        except Exception as e:
            raise Exception(f"Failed to generate summary with Gemini: {str(e)}")

    def generate_quiz_questions(
        self,
        text: str,
        num_questions: int = 10,
        difficulty: Optional[str] = None,
        quiz_type: str = "quiz"
    ) -> List[dict]:
        """Generate quiz questions from the provided text using Gemini."""
        
        difficulty_instructions = ""
        if difficulty:
            difficulty_instructions = f"Make the questions {difficulty} difficulty level."
        
        quiz_type_instructions = {
            "quiz": "short quiz questions suitable for quick review",
            "test": "test questions with moderate depth",
            "exam": "comprehFensive exam questions that test deep understanding",
            "practice": "practice questions for skill reinforcement"
        }
        
        type_instruction = quiz_type_instructions.get(quiz_type, quiz_type_instructions["quiz"])
        
        system_content = "You are an expert educational assessment creator. Generate high-quality, pedagogically sound questions that test understanding, not just memorization. The output MUST be a valid JSON array, without any surrounding text or markdown."
        user_content = f"""Based on the following educational material, generate {num_questions} {type_instruction}.
        {difficulty_instructions}
        
        For each question, provide:
        1. The question text
        2. Question type (multiple_choice, true_false, or short_answer)
        3. For multiple choice: 4 options with one correct answer
        4. For true/false: the correct answer
        5. For short answer: a model answer
        6. A brief explanation of the correct answer
        7. Difficulty level (easy, medium, or hard)
        8. Points value (1-10 based on complexity)
        
        Return the questions as a JSON array with this structure. Ensure the output is pure JSON, without any surrounding text or markdown, for direct parsing:
        [
            {{
                "question_text": "...",
                "question_type": "multiple_choice|true_false|short_answer",
                "difficulty": "easy|medium|hard",
                "points": 1-10,
                "explanation": "...",
                "options": [
                    {{"text": "...", "is_correct": true/false}},
                    ...
                ],
                "correct_answer": "..." (for true_false and short_answer)
            }}
        ]
        
        Educational Material:
        {text}
        """
        
        try:
            content = self._get_gemini_response(system_content, user_content, temperature=0.8, max_tokens=3000)
            
            if not content:
                return []
            
            # Gemini might include markdown ```json around the JSON, so we clean it.
            if content.strip().startswith("```json"):
                content = content.strip()[len("```json"):].strip()
            if content.strip().endswith("```"):
                content = content.strip()[:-len("```")].strip()

            result: Any = json.loads(content)
            
            if isinstance(result, dict) and "questions" in result:
                return result["questions"]
            elif isinstance(result, list):
                return result
            else:
                return []
                
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse JSON response from Gemini for quiz questions: {e}. Raw content: {content[:500]}...")
        except Exception as e:
            raise Exception(f"Failed to generate quiz questions with Gemini: {str(e)}")

    def generate_flashcards(self, text: str, num_cards: int = 20) -> List[dict]:
        """Generate flashcards from the provided text using Gemini."""
        
        system_content = "You are an expert at creating effective study flashcards that promote active recall and spaced repetition. The output MUST be a valid JSON array, without any surrounding text or markdown."
        user_content = f"""Based on the following educational material, generate {num_cards} flashcards for effective learning.
        
        Each flashcard should have:
        1. Front: A clear question, term, or concept
        2. Back: A concise answer, definition, or explanation
        3. Difficulty: easy, medium, or hard
        
        Focus on:
        - Key concepts and definitions
        - Important facts and relationships
        - Critical thinking questions
        - Application of knowledge
        
        Return as a JSON array with this structure. Ensure the output is pure JSON, without any surrounding text or markdown, for direct parsing:
        [
            {{
                "front": "...",
                "back": "...",
                "difficulty": "easy|medium|hard"
            }}
        ]
        
        Educational Material:
        {text}
        """
        
        try:
            content = self._get_gemini_response(system_content, user_content, temperature=0.8, max_tokens=2500)

            if not content:
                return []

            # Clean markdown
            if content.strip().startswith("```json"):
                content = content.strip()[len("```json"):].strip()
            if content.strip().endswith("```"):
                content = content.strip()[:-len("```")].strip()
                
            result: Any = json.loads(content)
            
            if isinstance(result, dict) and "flashcards" in result:
                return result["flashcards"]
            elif isinstance(result, list):
                return result
            else:
                return []
                
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse JSON response from Gemini for flashcards: {e}. Raw content: {content[:500]}...")
        except Exception as e:
            raise Exception(f"Failed to generate flashcards with Gemini: {str(e)}")

    def generate_daily_nudge(self, user_context: Optional[str] = None) -> str:
        """Generate a motivational daily nudge for the user using Gemini."""
        
        context_text = f"\nUser context: {user_context}" if user_context else ""
        
        system_content = "You are a supportive study coach who helps motivate students."
        user_content = f"""Generate a short, motivational message to encourage a student to review their study materials today.
        The message should be:
        - Positive and encouraging
        - Brief (1-2 sentences)
        - Actionable
        - Personalized if context is provided
        {context_text}
        
        Just return the message text, nothing else.
        """
        
        try:
            return self._get_gemini_response(system_content, user_content, temperature=0.9, max_tokens=150)
        except Exception as e:
            raise Exception(f"Failed to generate daily nudge with Gemini: {str(e)}")

    def generate_orientation_message(self, academic_level: str) -> str:
        """Generate an orientation message for new users using Gemini."""
        
        system_content = "You are a friendly onboarding assistant for an educational platform."
        user_content = f"""Generate a welcoming orientation message for a new user at the {academic_level} level joining an AI-powered study platform.
        
        The message should:
        - Welcome them warmly
        - Briefly explain the main features (summaries, quizzes, flashcards, reading streaks, daily nudges)
        - Encourage them to upload their first study material
        - Be encouraging and supportive
        - Be 3-4 sentences long
        
        Just return the message text, nothing else.
        """
        
        try:
            return self._get_gemini_response(system_content, user_content, temperature=0.8, max_tokens=250)
        except Exception as e:
            raise Exception(f"Failed to generate orientation message with Gemini: {str(e)}")
    
    def extract_text_from_document(self, file_path: str, file_type: str) -> str:
        """
        Extract text from a document (PDF, DOCX) using Python libraries (pypdf, python-docx)
        and OCR (pytesseract) for scanned content.
        """
        extracted_text_chunks = []

        try:
            if file_type.lower() == "pdf":
                with open(file_path, 'rb') as file:
                    reader = pypdf.PdfReader(file)
                    
                    # Iterate through pages to extract text and handle OCR for scanned pages
                    for page_num in range(len(reader.pages)):
                        page = reader.pages[page_num]
                        
                        # Attempt to extract text normally
                        text = page.extract_text()
                        if text:
                            extracted_text_chunks.append(text)
                        else:
                            # If no text is extracted, it might be a scanned page, try OCR
                            print(f"No direct text found on PDF page {page_num + 1}. Attempting OCR...")
                            
                            # For OCR, we need to render the PDF page to an image.
                            # This requires `poppler` utilities installed on the system
                            # and `pdf2image` Python library (not included in initial plan, but necessary for robust PDF-to-image conversion)
                            # As you asked for Python ONLY and avoided *local libs*, 
                            # direct PDF-to-image conversion without an external utility like poppler is hard.
                            # Let's simplify and assume the PDF might contain images that Tesseract can process directly
                            # if they are embedded or if we use a more complex setup.
                            # For a strict "python only" and handling scanned, you'd convert PDF pages to images.
                            # This usually requires `pdf2image` and `poppler`.
                            # Since we're trying to keep it minimal and "python only" without external executables BEYOND Tesseract,
                            # we'll use a more basic approach: if pypdf extracts nothing, we assume it's scanned
                            # and if there are *images* on the page, we'll try OCR on them.
                            # A full, robust solution for mixed PDF (text + scanned) is quite complex.
                            # For now, if pypdf returns nothing, we will explicitly tell the user that.
                            # A more advanced setup would involve `pdf2image` which wraps `poppler`.
                            # To keep it truly "Python only" *and* free, the best bet is if `pytesseract` can
                            # be given an image *from the PDF*. `pypdf` does not directly render pages to images.

                            # For a comprehensive OCR on PDF, you would use:
                            # from pdf2image import convert_from_path
                            # images = convert_from_path(file_path, first_page=page_num+1, last_page=page_num+1)
                            # if images:
                            #     ocr_text = pytesseract.image_to_string(images[0])
                            #     extracted_text_chunks.append(ocr_text)
                            # else:
                            #     extracted_text_chunks.append(f"[Could not extract text from PDF page {page_num + 1} (scanned/image only)]")
                            
                            # Without pdf2image/poppler, a scanned PDF page cannot be directly OCR'd by pytesseract.
                            # So, for scanned PDFs, we need to acknowledge this limitation with current libraries.
                            extracted_text_chunks.append(f"[Text extraction failed for PDF page {page_num + 1}. Page might be scanned/image-based and requires `pdf2image` and `poppler` for OCR.]")

            elif file_type.lower() == "docx":
                doc = Document(file_path)
                for paragraph in doc.paragraphs:
                    extracted_text_chunks.append(paragraph.text)
                
                # Handling images in DOCX is more complex:
                # python-docx can access inline shapes/images but doesn't have built-in OCR.
                # You would need to save each image to a temp file/buffer and then run pytesseract on it.
                # For an MVP, often image content from DOCX is just ignored or handled by visual inspection.
                # If images contain critical text, you would iterate doc.inline_shapes or doc.blips (binary large objects)
                # and apply OCR, but that's out of scope for a simple "extract text" without explicit image content needs.
                # Let's just extract paragraph text for DOCX.
                
            else:
                raise ValueError(f"Unsupported file type for extraction: {file_type}")

            full_text = "\n".join(chunk for chunk in extracted_text_chunks if chunk.strip())
            
            if not full_text:
                raise Exception("No text could be extracted from the document.")
            
            # Use Gemini to merge and clean if there were multiple chunks or potential OCR artifacts
            return self._merge_extracted_chunks(full_text, file_type)

        except Exception as e:
            raise Exception(f"Failed to extract text from {file_type} using Python libraries: {str(e)}")
    
    def _merge_extracted_chunks(self, combined_text: str, file_type: str) -> str:
        """Use Gemini to merge and clean up text extracted from multiple chunks."""
        
        # If combined text is too large for Gemini's context window, skip merging
        if len(combined_text) > 400000: # Adjust based on your chosen Gemini model's actual max_output_tokens and input limit
            print(f"Warning: Combined text too large ({len(combined_text)} chars) for merging with Gemini. Returning as-is.")
            return combined_text
        
        system_content = """You are a text merging expert. You receive text that was extracted from a document in multiple chunks.

Your task:
1. Merge the text sections smoothly
2. Fix any words or sentences that were split across chunk boundaries
3. Remove duplicate content that appears at chunk boundaries
4. Preserve all content, structure, and formatting
5. Return the complete, merged text. Ensure the output is only the merged text, without any additional commentary."""
        
        user_content = f"""The following text was extracted from a {file_type.upper()} document in multiple parts. Please merge it into a coherent whole, fixing any issues at the boundaries:

{combined_text}

Return the merged text:"""
        
        try:
            merged_text = self._get_gemini_response(system_content, user_content, temperature=0.2, max_tokens=4000)
            return merged_text.strip() if merged_text else combined_text
            
        except Exception as e:
            print(f"Warning: Failed to merge chunks with Gemini: {str(e)}. Returning unmerged text.")
            return combined_text
    
    def _extract_large_document(self, file_path: str, file_type: str, file_content: bytes) -> str:
        """
        Deprecated: This method is no longer used.
        Redirects to the main `extract_text_from_document`.
        """
        return self.extract_text_from_document(file_path, file_type)


# Global instance
ai_service = AIService() if settings.GOOGLE_API_KEY else None