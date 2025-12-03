from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List
from app.core.dependencies import get_session
from app.auth.dependencies import CurrentActiveUser
from app.materials.models import DailyNudge, DailyNudgeResponse
# Use optimized AI service for cost savings
from app.services.unified_ai_service import ai_service
from app.services.streak_service import streak_service
from datetime import datetime

router = APIRouter(prefix="/nudges", tags=["Daily Nudges"])


@router.post("/generate", response_model=DailyNudgeResponse, status_code=status.HTTP_201_CREATED)
async def generate_nudge(
    nudge_type: str = "daily",
    current_user: CurrentActiveUser = None,
    session: Session = Depends(get_session)
):
    """Generate a daily nudge or orientation message."""
    
    if not ai_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured"
        )
    
    # Get user's streak info for context
    streak = streak_service.get_or_create_streak(current_user.id, session)
    
    context = f"Current reading streak: {streak.current_streak} days"
    
    if nudge_type == "orientation":
        academic_level = current_user.profile.academic_level.value if current_user.profile.academic_level else "college"
        try:
            message = ai_service.generate_orientation_message(academic_level)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate orientation message: {str(e)}"
            )
    else:
        try:
            message = ai_service.generate_daily_nudge(context)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate daily nudge: {str(e)}"
            )
    
    # Save nudge
    nudge = DailyNudge(
        user_id=current_user.id,
        message=message,
        nudge_type=nudge_type
    )
    
    session.add(nudge)
    session.commit()
    session.refresh(nudge)
    
    return nudge


@router.get("/", response_model=List[DailyNudgeResponse])
async def list_nudges(
    unread_only: bool = False,
    current_user: CurrentActiveUser = None,
    session: Session = Depends(get_session)
):
    """Get all nudges for the current user."""
    
    stmt = select(DailyNudge).where(DailyNudge.user_id == current_user.id)
    
    if unread_only:
        stmt = stmt.where(DailyNudge.is_read == False)
    
    nudges = session.exec(stmt).all()
    return nudges


@router.get("/today", response_model=DailyNudgeResponse)
async def get_todays_nudge(
    current_user: CurrentActiveUser = None,
    session: Session = Depends(get_session)
):
    """Get today's nudge, generating one if it doesn't exist."""
    
    today = datetime.utcnow().date()
    
    # Check if there's already a nudge for today
    stmt = select(DailyNudge).where(
        DailyNudge.user_id == current_user.id,
        DailyNudge.nudge_type == "daily"
    ).order_by(DailyNudge.sent_at.desc())
    
    nudge = session.exec(stmt).first()
    
    if nudge and nudge.sent_at.date() == today:
        return nudge
    
    # Generate a new nudge for today
    if not ai_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured"
        )
    
    streak = streak_service.get_or_create_streak(current_user.id, session)
    context = f"Current reading streak: {streak.current_streak} days"
    
    try:
        message = ai_service.generate_daily_nudge(context)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate daily nudge: {str(e)}"
        )
    
    new_nudge = DailyNudge(
        user_id=current_user.id,
        message=message,
        nudge_type="daily"
    )
    
    session.add(new_nudge)
    session.commit()
    session.refresh(new_nudge)
    
    return new_nudge


@router.put("/{nudge_id}/read", response_model=DailyNudgeResponse)
async def mark_nudge_read(
    nudge_id: int,
    current_user: CurrentActiveUser = None,
    session: Session = Depends(get_session)
):
    """Mark a nudge as read."""
    
    stmt = select(DailyNudge).where(
        DailyNudge.id == nudge_id,
        DailyNudge.user_id == current_user.id
    )
    nudge = session.exec(stmt).first()
    
    if not nudge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nudge not found"
        )
    
    nudge.is_read = True
    session.add(nudge)
    session.commit()
    session.refresh(nudge)
    
    return nudge
