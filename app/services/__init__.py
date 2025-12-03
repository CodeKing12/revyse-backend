"""
Services module - exports optimized services for cost-effective AI operations.

The unified AI service provides:
- Response caching to avoid duplicate API calls
- Token usage tracking for cost monitoring
- Optimized prompts (shorter = fewer tokens = lower cost)
- Smart provider selection (Gemini direct preferred)

The optimized file service provides:
- Local text extraction first (FREE)
- AI fallback only when needed
- File content caching
"""

from app.services.unified_ai_service import ai_service, UnifiedAIService
from app.services.optimized_file_service import file_processing_service, OptimizedFileService
from app.services.streak_service import streak_service

__all__ = [
    'ai_service',
    'UnifiedAIService',
    'file_processing_service', 
    'OptimizedFileService',
    'streak_service'
]
