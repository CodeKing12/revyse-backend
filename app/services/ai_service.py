from openai import OpenAI
from app.core.config import settings
from typing import List, Optional
import json


class AIService:
    def __init__(self):
        if not settings.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY not found in settings")
        
        # OpenRouter uses OpenAI-compatible API
        self.client = OpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1"
        )
        self.model = settings.AI_MODEL
        
        # Extra headers for OpenRouter
        self.extra_headers = {
            "HTTP-Referer": "https://github.com/CodeKing12/revyse-backend",
            "X-Title": "Revyse Study App"
        }

    def generate_summary(self, text: str, summary_type: str = "general") -> str:
        """Generate a summary of the provided text."""
        
        prompts = {
            "general": "Create a comprehensive summary of the following educational material. Focus on key concepts, main ideas, and important details:",
            "brief": "Create a brief, concise summary of the following educational material, highlighting only the most important points:",
            "detailed": "Create a detailed, in-depth summary of the following educational material. Include all important concepts, explanations, and examples:"
        }
        
        prompt = prompts.get(summary_type, prompts["general"])
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert educational assistant that helps students understand and learn from their study materials."},
                    {"role": "user", "content": f"{prompt}\n\n{text}"}
                ],
                temperature=0.7,
                max_tokens=2000,
                extra_headers=self.extra_headers
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Failed to generate summary: {str(e)}")

    def generate_quiz_questions(
        self,
        text: str,
        num_questions: int = 10,
        difficulty: Optional[str] = None,
        quiz_type: str = "quiz"
    ) -> List[dict]:
        """Generate quiz questions from the provided text."""
        
        difficulty_instructions = ""
        if difficulty:
            difficulty_instructions = f"Make the questions {difficulty} difficulty level."
        
        quiz_type_instructions = {
            "quiz": "short quiz questions suitable for quick review",
            "test": "test questions with moderate depth",
            "exam": "comprehensive exam questions that test deep understanding",
            "practice": "practice questions for skill reinforcement"
        }
        
        type_instruction = quiz_type_instructions.get(quiz_type, quiz_type_instructions["quiz"])
        
        prompt = f"""Based on the following educational material, generate {num_questions} {type_instruction}.
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
        
        Return the questions as a JSON array with this structure:
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
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert educational assessment creator. Generate high-quality, pedagogically sound questions that test understanding, not just memorization."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=3000,
                response_format={"type": "json_object"},
                extra_headers=self.extra_headers
            )
            
            content = response.choices[0].message.content
            result = json.loads(content)
            
            # Handle both array and object with questions key
            if isinstance(result, dict) and "questions" in result:
                return result["questions"]
            elif isinstance(result, list):
                return result
            else:
                return []
                
        except Exception as e:
            raise Exception(f"Failed to generate quiz questions: {str(e)}")

    def generate_flashcards(self, text: str, num_cards: int = 20) -> List[dict]:
        """Generate flashcards from the provided text."""
        
        prompt = f"""Based on the following educational material, generate {num_cards} flashcards for effective learning.
        
        Each flashcard should have:
        1. Front: A clear question, term, or concept
        2. Back: A concise answer, definition, or explanation
        3. Difficulty: easy, medium, or hard
        
        Focus on:
        - Key concepts and definitions
        - Important facts and relationships
        - Critical thinking questions
        - Application of knowledge
        
        Return as a JSON array with this structure:
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
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert at creating effective study flashcards that promote active recall and spaced repetition."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=2500,
                response_format={"type": "json_object"},
                extra_headers=self.extra_headers
            )
            
            content = response.choices[0].message.content
            result = json.loads(content)
            
            # Handle both array and object with flashcards key
            if isinstance(result, dict) and "flashcards" in result:
                return result["flashcards"]
            elif isinstance(result, list):
                return result
            else:
                return []
                
        except Exception as e:
            raise Exception(f"Failed to generate flashcards: {str(e)}")

    def generate_daily_nudge(self, user_context: Optional[str] = None) -> str:
        """Generate a motivational daily nudge for the user."""
        
        context_text = f"\nUser context: {user_context}" if user_context else ""
        
        prompt = f"""Generate a short, motivational message to encourage a student to review their study materials today.
        The message should be:
        - Positive and encouraging
        - Brief (1-2 sentences)
        - Actionable
        - Personalized if context is provided
        {context_text}
        
        Just return the message text, nothing else.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a supportive study coach who helps motivate students."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.9,
                max_tokens=150,
                extra_headers=self.extra_headers
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Failed to generate daily nudge: {str(e)}")

    def generate_orientation_message(self, academic_level: str) -> str:
        """Generate an orientation message for new users."""
        
        prompt = f"""Generate a welcoming orientation message for a new user at the {academic_level} level joining an AI-powered study platform.
        
        The message should:
        - Welcome them warmly
        - Briefly explain the main features (summaries, quizzes, flashcards, reading streaks, daily nudges)
        - Encourage them to upload their first study material
        - Be encouraging and supportive
        - Be 3-4 sentences long
        
        Just return the message text, nothing else.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a friendly onboarding assistant for an educational platform."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=250,
                extra_headers=self.extra_headers
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Failed to generate orientation message: {str(e)}")


# Global instance
ai_service = AIService() if settings.OPENROUTER_API_KEY else None
