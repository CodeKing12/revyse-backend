from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.core.dependencies import get_session
from app.auth.dependencies import CurrentActiveUser
from app.materials.models import ReadingStreakResponse
from app.services.streak_service import streak_service

router = APIRouter(prefix="/streaks", tags=["Reading Streaks"])


@router.get("/", response_model=ReadingStreakResponse)
async def get_streak(
    current_user: CurrentActiveUser = None,
    session: Session = Depends(get_session)
):
    """Get the current user's reading streak."""
    
    streak = streak_service.get_or_create_streak(current_user.id, session)
    
    return ReadingStreakResponse(
        current_streak=streak.current_streak,
        longest_streak=streak.longest_streak,
        last_activity_date=streak.last_activity_date,
        total_reading_days=streak.total_reading_days
    )


@router.post("/record")
async def record_activity(
    current_user: CurrentActiveUser = None,
    session: Session = Depends(get_session)
):
    """Manually record a reading activity to update streak."""
    
    streak = streak_service.update_streak(current_user.id, session)
    
    return {
        "message": "Activity recorded successfully",
        "current_streak": streak.current_streak,
        "longest_streak": streak.longest_streak
    }


@router.get("/status")
async def get_streak_status(
    current_user: CurrentActiveUser = None,
    session: Session = Depends(get_session)
):
    """Check the status of the reading streak."""
    
    status = streak_service.check_streak_status(current_user.id, session)
    
    return status
