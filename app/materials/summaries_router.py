from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List
from app.core.dependencies import get_session
from app.auth.dependencies import CurrentActiveUser
from app.materials.models import (
    Material, Summary, SummaryCreate, SummaryResponse
)
# Use optimized AI service for cost savings
from app.services.unified_ai_service import ai_service
from app.services.streak_service import streak_service

router = APIRouter(prefix="/summaries", tags=["Summaries"])


@router.post("/", response_model=SummaryResponse, status_code=status.HTTP_201_CREATED)
async def create_summary(
    data: SummaryCreate,
    current_user: CurrentActiveUser = None,
    session: Session = Depends(get_session)
):
    """Generate a summary for a material."""
    
    if not ai_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured"
        )
    
    # Get material
    stmt = select(Material).where(
        Material.id == data.material_id,
        Material.user_id == current_user.id
    )
    material = session.exec(stmt).first()
    
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material not found"
        )
    
    if not material.extracted_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Material has no extracted text"
        )
    
    # Generate summary using AI
    try:
        summary_content = ai_service.generate_summary(
            material.extracted_text,
            data.summary_type
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate summary: {str(e)}"
        )
    
    # Save summary
    summary = Summary(
        material_id=data.material_id,
        content=summary_content,
        summary_type=data.summary_type,
        user_id=current_user.id
    )
    
    session.add(summary)
    session.commit()
    session.refresh(summary)
    
    # Update reading streak
    streak_service.update_streak(current_user.id, session)
    
    return summary


@router.get("/material/{material_id}", response_model=List[SummaryResponse])
async def get_material_summaries(
    material_id: int,
    current_user: CurrentActiveUser = None,
    session: Session = Depends(get_session)
):
    """Get all summaries for a specific material."""
    
    # Verify material belongs to user
    mat_stmt = select(Material).where(
        Material.id == material_id,
        Material.user_id == current_user.id
    )
    material = session.exec(mat_stmt).first()
    
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material not found"
        )
    
    stmt = select(Summary).where(Summary.material_id == material_id)
    summaries = session.exec(stmt).all()
    return summaries


@router.get("/{summary_id}", response_model=SummaryResponse)
async def get_summary(
    summary_id: int,
    current_user: CurrentActiveUser = None,
    session: Session = Depends(get_session)
):
    """Get a specific summary."""
    stmt = select(Summary).where(
        Summary.id == summary_id,
        Summary.user_id == current_user.id
    )
    summary = session.exec(stmt).first()
    
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Summary not found"
        )
    
    # Update reading streak when viewing summary
    streak_service.update_streak(current_user.id, session)
    
    return summary


@router.delete("/{summary_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_summary(
    summary_id: int,
    current_user: CurrentActiveUser = None,
    session: Session = Depends(get_session)
):
    """Delete a summary."""
    stmt = select(Summary).where(
        Summary.id == summary_id,
        Summary.user_id == current_user.id
    )
    summary = session.exec(stmt).first()
    
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Summary not found"
        )
    
    session.delete(summary)
    session.commit()
    
    return None
