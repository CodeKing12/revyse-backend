from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List
from app.core.dependencies import get_session
from app.auth.dependencies import CurrentActiveUser
from app.materials.models import (
    Material, FlashCard, FlashCardCreate, FlashCardResponse
)
# Use optimized AI service for cost savings
from app.services.unified_ai_service import ai_service
from app.services.streak_service import streak_service
from datetime import datetime

router = APIRouter(prefix="/flashcards", tags=["Flashcards"])


@router.post("/", response_model=List[FlashCardResponse], status_code=status.HTTP_201_CREATED)
async def create_flashcards(
    data: FlashCardCreate,
    current_user: CurrentActiveUser = None,
    session: Session = Depends(get_session)
):
    """Generate flashcards from materials using AI."""
    
    if not ai_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured"
        )
    
    # Get materials and combine their text
    materials_text = []
    for material_id in data.material_ids:
        stmt = select(Material).where(
            Material.id == material_id,
            Material.user_id == current_user.id
        )
        material = session.exec(stmt).first()
        
        if not material:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Material {material_id} not found"
            )
        
        if material.extracted_text:
            materials_text.append(material.extracted_text)
    
    if not materials_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No text content found in materials"
        )
    
    combined_text = "\n\n".join(materials_text)
    
    # Generate flashcards using AI
    try:
        flashcards_data = ai_service.generate_flashcards(
            combined_text,
            num_cards=data.num_cards
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate flashcards: {str(e)}"
        )
    
    # Create flashcards
    flashcards = []
    for fc_data in flashcards_data:
        flashcard = FlashCard(
            material_id=data.material_ids[0] if len(data.material_ids) == 1 else None,
            user_id=current_user.id,
            front=fc_data.get("front", ""),
            back=fc_data.get("back", ""),
            difficulty=fc_data.get("difficulty", "medium")
        )
        session.add(flashcard)
        session.commit()
        session.refresh(flashcard)
        flashcards.append(flashcard)
    
    # Update reading streak
    streak_service.update_streak(current_user.id, session)
    
    return flashcards


@router.get("/", response_model=List[FlashCardResponse])
async def list_flashcards(
    material_id: int = None,
    current_user: CurrentActiveUser = None,
    session: Session = Depends(get_session)
):
    """Get all flashcards for the current user, optionally filtered by material."""
    
    if material_id:
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
        
        stmt = select(FlashCard).where(
            FlashCard.material_id == material_id,
            FlashCard.user_id == current_user.id
        )
    else:
        stmt = select(FlashCard).where(FlashCard.user_id == current_user.id)
    
    flashcards = session.exec(stmt).all()
    return flashcards


@router.get("/{flashcard_id}", response_model=FlashCardResponse)
async def get_flashcard(
    flashcard_id: int,
    current_user: CurrentActiveUser = None,
    session: Session = Depends(get_session)
):
    """Get a specific flashcard."""
    stmt = select(FlashCard).where(
        FlashCard.id == flashcard_id,
        FlashCard.user_id == current_user.id
    )
    flashcard = session.exec(stmt).first()
    
    if not flashcard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flashcard not found"
        )
    
    return flashcard


@router.post("/{flashcard_id}/review", response_model=FlashCardResponse)
async def review_flashcard(
    flashcard_id: int,
    quality: int,  # 0-5, how well the user knew the answer
    current_user: CurrentActiveUser = None,
    session: Session = Depends(get_session)
):
    """Mark a flashcard as reviewed and update mastery level."""
    
    if quality < 0 or quality > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quality must be between 0 and 5"
        )
    
    stmt = select(FlashCard).where(
        FlashCard.id == flashcard_id,
        FlashCard.user_id == current_user.id
    )
    flashcard = session.exec(stmt).first()
    
    if not flashcard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flashcard not found"
        )
    
    # Update review stats
    flashcard.last_reviewed = datetime.utcnow()
    flashcard.review_count += 1
    
    # Update mastery level based on quality (simple algorithm)
    if quality >= 4:
        flashcard.mastery_level = min(5, flashcard.mastery_level + 1)
    elif quality <= 2:
        flashcard.mastery_level = max(0, flashcard.mastery_level - 1)
    
    session.add(flashcard)
    session.commit()
    session.refresh(flashcard)
    
    # Update reading streak
    streak_service.update_streak(current_user.id, session)
    
    return flashcard


@router.delete("/{flashcard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flashcard(
    flashcard_id: int,
    current_user: CurrentActiveUser = None,
    session: Session = Depends(get_session)
):
    """Delete a flashcard."""
    stmt = select(FlashCard).where(
        FlashCard.id == flashcard_id,
        FlashCard.user_id == current_user.id
    )
    flashcard = session.exec(stmt).first()
    
    if not flashcard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flashcard not found"
        )
    
    session.delete(flashcard)
    session.commit()
    
    return None


@router.post("/batch", response_model=List[FlashCardResponse], status_code=status.HTTP_201_CREATED)
async def create_flashcards_batch(
    material_ids: List[int],
    num_cards_per_material: int = 10,
    current_user: CurrentActiveUser = None,
    session: Session = Depends(get_session)
):
    """
    Generate flashcards from multiple materials in a single optimized API call.
    This is more cost-effective than generating flashcards one material at a time.
    
    - material_ids: List of material IDs to generate flashcards from
    - num_cards_per_material: Number of cards to generate per material (capped at 50 total)
    """
    
    if not ai_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured"
        )
    
    if len(material_ids) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 materials per batch request"
        )
    
    # Gather all material texts
    materials_texts = []
    for material_id in material_ids:
        stmt = select(Material).where(
            Material.id == material_id,
            Material.user_id == current_user.id
        )
        material = session.exec(stmt).first()
        
        if not material:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Material {material_id} not found"
            )
        
        if material.extracted_text:
            materials_texts.append(material.extracted_text)
    
    if not materials_texts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No text content found in materials"
        )
    
    # Use batch generation (single API call for all materials)
    try:
        flashcards_data = ai_service.generate_flashcards_batch(
            materials_texts,
            num_cards_per_text=num_cards_per_material
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate flashcards: {str(e)}"
        )
    
    # Create flashcards
    flashcards = []
    for fc_data in flashcards_data:
        flashcard = FlashCard(
            material_id=material_ids[0] if len(material_ids) == 1 else None,
            user_id=current_user.id,
            front=fc_data.get("front", ""),
            back=fc_data.get("back", ""),
            difficulty=fc_data.get("difficulty", "medium")
        )
        session.add(flashcard)
        session.commit()
        session.refresh(flashcard)
        flashcards.append(flashcard)
    
    # Update reading streak
    streak_service.update_streak(current_user.id, session)
    
    return flashcards
