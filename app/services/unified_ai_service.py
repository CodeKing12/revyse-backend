"""
Unified AI Service with Cost Optimizations
- Supports multiple providers (Google Gemini direct, OpenRouter)
- Response caching to avoid duplicate API calls
- Token usage tracking for cost monitoring
- Optimized prompts for efficiency
- Smart fallback between providers
"""

from openai import OpenAI
from app.core.config import settings
from typing import List, Optional, Any, Dict, Tuple
import json
import hashlib
import time
from datetime import datetime, timedelta
from functools import lru_cache
from dataclasses import dataclass, field

# Try to import Google Generative AI
try:
    import google.generativeai as genai  # type: ignore
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None  # type: ignore


@dataclass
class TokenUsage:
    """Track token usage for cost monitoring."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_calls: int = 0
    cached_hits: int = 0
    
    def add_usage(self, input_tokens: int, output_tokens: int, cached: bool = False):
        if cached:
            self.cached_hits += 1
        else:
            self.input_tokens += input_tokens
            self.output_tokens += output_tokens
            self.total_calls += 1
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_calls": self.total_calls,
            "cached_hits": self.cached_hits,
            "estimated_cost_usd": self.estimate_cost()
        }
    
    def estimate_cost(self) -> float:
        """Estimate cost based on Gemini Flash pricing ($0.075/1M input, $0.30/1M output)."""
        input_cost = (self.input_tokens / 1_000_000) * 0.075
        output_cost = (self.output_tokens / 1_000_000) * 0.30
        return round(input_cost + output_cost, 6)


@dataclass
class CacheEntry:
    """Cache entry with TTL support."""
    value: Any
    created_at: datetime
    ttl_seconds: int = 3600  # Default 1 hour
    
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.created_at + timedelta(seconds=self.ttl_seconds)


class ResponseCache:
    """Simple in-memory cache for AI responses."""
    
    def __init__(self, max_size: int = 500):
        self._cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
    
    def _generate_key(self, operation: str, content: str, **kwargs) -> str:
        """Generate cache key from operation and content hash."""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:16]
        params = json.dumps(kwargs, sort_keys=True) if kwargs else ""
        return f"{operation}:{content_hash}:{hashlib.md5(params.encode()).hexdigest()[:8]}"
    
    def get(self, operation: str, content: str, **kwargs) -> Optional[Any]:
        """Get cached response if exists and not expired."""
        key = self._generate_key(operation, content, **kwargs)
        entry = self._cache.get(key)
        if entry and not entry.is_expired():
            return entry.value
        elif entry:
            del self._cache[key]  # Clean expired
        return None
    
    def set(self, operation: str, content: str, value: Any, ttl_seconds: int = 3600, **kwargs):
        """Cache response with TTL."""
        if len(self._cache) >= self.max_size:
            self._cleanup_expired()
            if len(self._cache) >= self.max_size:
                # Remove oldest entries
                oldest_keys = sorted(self._cache.keys(), 
                                    key=lambda k: self._cache[k].created_at)[:self.max_size // 4]
                for k in oldest_keys:
                    del self._cache[k]
        
        key = self._generate_key(operation, content, **kwargs)
        self._cache[key] = CacheEntry(value=value, created_at=datetime.utcnow(), ttl_seconds=ttl_seconds)
    
    def _cleanup_expired(self):
        """Remove expired entries."""
        expired_keys = [k for k, v in self._cache.items() if v.is_expired()]
        for k in expired_keys:
            del self._cache[k]


class UnifiedAIService:
    """
    Unified AI service with cost optimizations:
    1. Response caching for identical requests
    2. Token usage tracking
    3. Optimized prompts (shorter, more efficient)
    4. Smart provider selection (Gemini direct preferred for cost)
    """
    
    def __init__(self):
        self.cache = ResponseCache()
        self.token_usage = TokenUsage()
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize available AI clients based on configuration."""
        self.gemini_client = None
        self.openrouter_client = None
        self.primary_provider = None
        
        # Prefer Gemini direct (cheaper and faster)
        if GEMINI_AVAILABLE and settings.GOOGLE_API_KEY:
            try:
                genai.configure(api_key=settings.GOOGLE_API_KEY)  # type: ignore
                self.gemini_model_name = getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash')
                self.gemini_client = genai.GenerativeModel(self.gemini_model_name)  # type: ignore
                self.primary_provider = "gemini"
            except Exception as e:
                print(f"Warning: Failed to initialize Gemini: {e}")
        
        # OpenRouter as fallback
        if settings.OPENROUTER_API_KEY:
            try:
                self.openrouter_client = OpenAI(
                    api_key=settings.OPENROUTER_API_KEY,
                    base_url="https://openrouter.ai/api/v1"
                )
                self.openrouter_model = getattr(settings, 'AI_MODEL', 'google/gemini-flash-1.5')
                self.openrouter_headers = {
                    "HTTP-Referer": "https://github.com/CodeKing12/revyse-backend",
                    "X-Title": "Revyse Study App"
                }
                if not self.primary_provider:
                    self.primary_provider = "openrouter"
            except Exception as e:
                print(f"Warning: Failed to initialize OpenRouter: {e}")
        
        if not self.primary_provider:
            raise ValueError("No AI provider configured. Set GOOGLE_API_KEY or OPENROUTER_API_KEY")
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars ≈ 1 token)."""
        return len(text) // 4
    
    def _get_gemini_response(self, system_content: str, user_content: str,
                             temperature: float = 0.7, max_tokens: int = 2000) -> Tuple[str, int, int]:
        """Get response from Gemini and return (content, input_tokens, output_tokens)."""
        if not self.gemini_client or not genai:
            raise Exception("Gemini client not initialized")
            
        combined = f"Instruction: {system_content}\n\nTask: {user_content}"
        input_tokens = self._estimate_tokens(combined)
        
        generation_config = genai.types.GenerationConfig(  # type: ignore
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        
        response = self.gemini_client.generate_content(
            [{"role": "user", "parts": [combined]}],
            generation_config=generation_config
        )
        
        content = ""
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            content = response.candidates[0].content.parts[0].text
        
        output_tokens = self._estimate_tokens(content)
        return content, input_tokens, output_tokens
    
    def _get_openrouter_response(self, system_content: str, user_content: str,
                                  temperature: float = 0.7, max_tokens: int = 2000,
                                  json_mode: bool = False) -> Tuple[str, int, int]:
        """Get response from OpenRouter and return (content, input_tokens, output_tokens)."""
        if not self.openrouter_client:
            raise Exception("OpenRouter client not initialized")
            
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]
        
        input_tokens = self._estimate_tokens(system_content + user_content)
        
        kwargs: Dict[str, Any] = {
            "model": self.openrouter_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "extra_headers": self.openrouter_headers
        }
        
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        
        response = self.openrouter_client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""
        output_tokens = self._estimate_tokens(content)
        
        return content, input_tokens, output_tokens
    
    def _get_ai_response(self, system_content: str, user_content: str,
                         temperature: float = 0.7, max_tokens: int = 2000,
                         json_mode: bool = False) -> str:
        """Get AI response with automatic provider fallback."""
        if self.primary_provider == "gemini" and self.gemini_client:
            try:
                content, in_tok, out_tok = self._get_gemini_response(
                    system_content, user_content, temperature, max_tokens
                )
                self.token_usage.add_usage(in_tok, out_tok)
                return content
            except Exception as e:
                if self.openrouter_client:
                    print(f"Gemini failed, falling back to OpenRouter: {e}")
                else:
                    raise
        
        if self.openrouter_client:
            content, in_tok, out_tok = self._get_openrouter_response(
                system_content, user_content, temperature, max_tokens, json_mode
            )
            self.token_usage.add_usage(in_tok, out_tok)
            return content
        
        raise Exception("No AI provider available")
    
    def _clean_json_response(self, content: str) -> str:
        """Clean markdown from JSON responses."""
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return content.strip()
    
    def _parse_json_response(self, content: str, fallback_key: Optional[str] = None) -> Any:
        """Parse JSON response, handling various formats."""
        content = self._clean_json_response(content)
        result = json.loads(content)
        
        if fallback_key and isinstance(result, dict) and fallback_key in result:
            return result[fallback_key]
        return result if isinstance(result, list) else []

    # ============ OPTIMIZED METHODS ============

    def generate_summary(self, text: str, summary_type: str = "general") -> str:
        """Generate summary with caching for identical content."""
        # Check cache first
        cached = self.cache.get("summary", text, summary_type=summary_type)
        if cached:
            self.token_usage.add_usage(0, 0, cached=True)
            return cached
        
        # Truncate very long texts to save tokens (keep first 30k chars)
        truncated = text[:30000] if len(text) > 30000 else text
        
        # Optimized prompts (shorter = fewer tokens)
        prompts = {
            "general": "Summarize this study material, covering key concepts and main ideas:",
            "brief": "Provide a concise 3-5 point summary of key takeaways:",
            "detailed": "Create a detailed summary with concepts, explanations, and examples:"
        }
        
        system = "You are an educational assistant creating study summaries."
        user = f"{prompts.get(summary_type, prompts['general'])}\n\n{truncated}"
        
        result = self._get_ai_response(system, user, temperature=0.7, max_tokens=1500)
        
        # Cache for 24 hours (summaries don't change)
        self.cache.set("summary", text, result, ttl_seconds=86400, summary_type=summary_type)
        return result

    def generate_quiz_questions(
        self,
        text: str,
        num_questions: int = 10,
        difficulty: Optional[str] = None,
        quiz_type: str = "quiz"
    ) -> List[dict]:
        """Generate quiz questions with caching."""
        cache_key_params = {"num": num_questions, "diff": difficulty, "type": quiz_type}
        cached = self.cache.get("quiz", text[:5000], **cache_key_params)  # Use truncated for cache key
        if cached:
            self.token_usage.add_usage(0, 0, cached=True)
            return cached
        
        # Truncate to save tokens
        truncated = text[:25000] if len(text) > 25000 else text
        
        diff_instruction = f"Difficulty: {difficulty}. " if difficulty else ""
        
        system = "Generate educational assessment questions. Return ONLY a JSON array."
        user = f"""Generate {num_questions} {quiz_type} questions. {diff_instruction}

Return JSON array:
[{{"question_text": "...", "question_type": "multiple_choice|true_false|short_answer", "difficulty": "easy|medium|hard", "points": 1-10, "explanation": "...", "options": [{{"text": "...", "is_correct": true/false}}], "correct_answer": "..."}}]

Content:
{truncated}"""
        
        content = self._get_ai_response(system, user, temperature=0.8, max_tokens=2500, json_mode=True)
        
        try:
            result = self._parse_json_response(content, "questions")
            self.cache.set("quiz", text[:5000], result, ttl_seconds=3600, **cache_key_params)
            return result
        except json.JSONDecodeError:
            return []

    def generate_flashcards(self, text: str, num_cards: int = 20) -> List[dict]:
        """Generate flashcards with caching."""
        cache_params = {"num": num_cards}
        cached = self.cache.get("flashcards", text[:5000], **cache_params)
        if cached:
            self.token_usage.add_usage(0, 0, cached=True)
            return cached
        
        truncated = text[:25000] if len(text) > 25000 else text
        
        system = "Create study flashcards. Return ONLY a JSON array."
        user = f"""Generate {num_cards} flashcards for spaced repetition study.

Return JSON array:
[{{"front": "question/term", "back": "answer/definition", "difficulty": "easy|medium|hard"}}]

Content:
{truncated}"""
        
        content = self._get_ai_response(system, user, temperature=0.8, max_tokens=2000, json_mode=True)
        
        try:
            result = self._parse_json_response(content, "flashcards")
            self.cache.set("flashcards", text[:5000], result, ttl_seconds=3600, **cache_params)
            return result
        except json.JSONDecodeError:
            return []

    def generate_flashcards_batch(self, texts: List[str], num_cards_per_text: int = 10) -> List[dict]:
        """Generate flashcards from multiple texts in one API call (batch processing)."""
        combined = "\n\n---NEW MATERIAL---\n\n".join(t[:8000] for t in texts)
        total_cards = min(num_cards_per_text * len(texts), 50)  # Cap at 50
        
        return self.generate_flashcards(combined, total_cards)

    def generate_daily_nudge(self, user_context: Optional[str] = None) -> str:
        """Generate motivational nudge (no caching - should be unique)."""
        context = f" Context: {user_context}" if user_context else ""
        
        system = "You are a supportive study coach."
        user = f"Generate a brief (1-2 sentence) motivational message for a student.{context}"
        
        return self._get_ai_response(system, user, temperature=0.9, max_tokens=100)

    def generate_orientation_message(self, academic_level: str) -> str:
        """Generate welcome message for new users."""
        # Cache orientation messages by level
        cached = self.cache.get("orientation", academic_level)
        if cached:
            self.token_usage.add_usage(0, 0, cached=True)
            return cached
        
        system = "You are a friendly onboarding assistant for an educational platform."
        user = f"Welcome a new {academic_level} level student to Revyse. Mention: summaries, quizzes, flashcards, streaks. 2-3 sentences max."
        
        result = self._get_ai_response(system, user, temperature=0.8, max_tokens=150)
        self.cache.set("orientation", academic_level, result, ttl_seconds=86400)
        return result

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current token usage statistics."""
        return self.token_usage.get_stats()

    def reset_usage_stats(self):
        """Reset token usage counters."""
        self.token_usage = TokenUsage()


# Global instance
ai_service = None
try:
    ai_service = UnifiedAIService()
except Exception as e:
    print(f"Warning: AI service initialization failed: {e}")
