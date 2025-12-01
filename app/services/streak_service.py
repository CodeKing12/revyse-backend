from datetime import datetime, timedelta
from sqlmodel import Session, select
from app.materials.models import ReadingStreak


class StreakService:
    """Service for managing user reading streaks."""
    
    @staticmethod
    def get_or_create_streak(user_id: int, session: Session) -> ReadingStreak:
        """Get or create a reading streak for a user."""
        stmt = select(ReadingStreak).where(ReadingStreak.user_id == user_id)
        streak = session.exec(stmt).first()
        
        if not streak:
            streak = ReadingStreak(user_id=user_id)
            session.add(streak)
            session.commit()
            session.refresh(streak)
        
        return streak
    
    @staticmethod
    def update_streak(user_id: int, session: Session) -> ReadingStreak:
        """Update the user's reading streak based on activity."""
        streak = StreakService.get_or_create_streak(user_id, session)
        
        today = datetime.utcnow().date()
        last_activity = streak.last_activity_date.date() if streak.last_activity_date else None
        
        # If activity is today, no need to update
        if last_activity == today:
            return streak
        
        # If activity was yesterday, increment streak
        if last_activity and last_activity == today - timedelta(days=1):
            streak.current_streak += 1
            streak.total_reading_days += 1
        # If activity was today (first time), start streak
        elif not last_activity:
            streak.current_streak = 1
            streak.total_reading_days = 1
        # If streak was broken, reset
        else:
            streak.current_streak = 1
            streak.total_reading_days += 1
        
        # Update longest streak if current is higher
        if streak.current_streak > streak.longest_streak:
            streak.longest_streak = streak.current_streak
        
        streak.last_activity_date = datetime.utcnow()
        streak.updated_at = datetime.utcnow()
        
        session.add(streak)
        session.commit()
        session.refresh(streak)
        
        return streak
    
    @staticmethod
    def check_streak_status(user_id: int, session: Session) -> dict:
        """Check if the streak is at risk of breaking."""
        streak = StreakService.get_or_create_streak(user_id, session)
        
        if not streak.last_activity_date:
            return {
                "status": "new",
                "message": "Start your reading streak today!",
                "days_until_break": 0
            }
        
        today = datetime.utcnow().date()
        last_activity = streak.last_activity_date.date()
        days_since_activity = (today - last_activity).days
        
        if days_since_activity == 0:
            return {
                "status": "active",
                "message": f"Great job! Your streak is at {streak.current_streak} days!",
                "days_until_break": 1
            }
        elif days_since_activity == 1:
            return {
                "status": "at_risk",
                "message": "Don't break your streak! Read something today.",
                "days_until_break": 0
            }
        else:
            return {
                "status": "broken",
                "message": "Your streak was broken. Start a new one today!",
                "days_until_break": 0
            }


streak_service = StreakService()
