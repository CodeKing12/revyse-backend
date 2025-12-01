"""
Admin router for monitoring and management endpoints.
Provides access to usage statistics, cache management, and system health.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.auth.dependencies import CurrentActiveUser
from app.services.unified_ai_service import ai_service
from app.services.optimized_file_service import file_processing_service
from typing import Dict, Any, Optional

router = APIRouter(prefix="/admin", tags=["Admin & Monitoring"])


@router.get("/usage-stats", response_model=Dict[str, Any])
async def get_usage_stats(
    current_user: CurrentActiveUser
):
    """
    Get AI usage statistics including:
    - Total API calls made
    - Tokens used (input/output)
    - Cache hit rate
    - Estimated cost
    
    Useful for monitoring and cost management.
    """
    if not ai_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service not configured"
        )
    
    ai_stats = ai_service.get_usage_stats()
    file_stats = file_processing_service.get_cache_stats()
    
    # Calculate cache efficiency
    total_requests = ai_stats["total_calls"] + ai_stats["cached_hits"]
    cache_hit_rate = (ai_stats["cached_hits"] / total_requests * 100) if total_requests > 0 else 0
    
    return {
        "ai_usage": ai_stats,
        "file_cache": file_stats,
        "efficiency": {
            "cache_hit_rate_percent": round(cache_hit_rate, 2),
            "total_requests": total_requests,
            "api_calls_saved": ai_stats["cached_hits"]
        },
        "cost_savings_estimate": {
            "description": "Estimated savings from caching",
            "calls_saved": ai_stats["cached_hits"],
            "estimated_usd_saved": round(ai_stats["cached_hits"] * 0.001, 4)  # Rough estimate
        }
    }


@router.post("/clear-cache")
async def clear_caches(
    current_user: CurrentActiveUser
):
    """Clear all caches (AI response cache and file extraction cache)."""
    if ai_service:
        ai_service.cache._cache.clear()
    
    file_processing_service.clear_cache()
    
    return {"message": "All caches cleared successfully"}


@router.post("/reset-usage-stats")
async def reset_usage_stats(
    current_user: CurrentActiveUser
):
    """Reset AI usage statistics counters."""
    if not ai_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service not configured"
        )
    
    ai_service.reset_usage_stats()
    return {"message": "Usage statistics reset successfully"}


@router.get("/health")
async def health_check():
    """
    System health check endpoint.
    Returns status of AI service, file processing service, and OCR capabilities.
    """
    ocr_caps = file_processing_service.get_ocr_capabilities()
    
    return {
        "status": "healthy",
        "services": {
            "ai_service": "available" if ai_service else "unavailable",
            "ai_provider": ai_service.primary_provider if ai_service else None,
            "file_service": "available"
        },
        "ocr_capabilities": ocr_caps
    }
