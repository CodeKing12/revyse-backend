from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlmodel import Session, select
from typing import List
from app.core.dependencies import get_session
from app.auth.dependencies import CurrentActiveUser
from app.materials.models import (
    Material, MaterialCreate, MaterialResponse, MaterialType,
    Summary, SummaryCreate, SummaryResponse
)
from app.services.file_service import file_processing_service
from app.services.ai_service import ai_service
from app.services.streak_service import streak_service
from app.core.config import settings
import os
import shutil
from datetime import datetime

router = APIRouter(prefix="/materials", tags=["Materials"])


@router.post("/upload", response_model=MaterialResponse, status_code=status.HTTP_201_CREATED)
async def upload_material(
    file: UploadFile = File(...),
    title: str = None,
    description: str = None,
    material_type: MaterialType = MaterialType.OTHER,
    course_id: int = None,  # Optional course assignment
    current_user: CurrentActiveUser = None,
    session: Session = Depends(get_session)
):
    """Upload a study material file (PDF, DOCX, TXT). Can optionally be assigned to a course."""
    
    # Validate file type
    allowed_extensions = {'.pdf', '.docx', '.doc', '.txt'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_ext} not supported. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    # If course_id provided, verify it belongs to user
    if course_id is not None:
        from app.materials.models import Course
        course_stmt = select(Course).where(
            Course.id == course_id,
            Course.user_id == current_user.id
        )
        course = session.exec(course_stmt).first()
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
    
    # Create upload directory if it doesn't exist
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{current_user.id}_{timestamp}_{file.filename}"
    file_path = os.path.join(upload_dir, safe_filename)
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    
    # Extract text from file
    try:
        extracted_text = file_processing_service.extract_text(file_path, file_ext)
    except Exception as e:
        # Clean up file if text extraction fails
        os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract text from file: {str(e)}"
        )
    
    # Create material record
    material = Material(
        title=title or file.filename,
        description=description,
        file_path=file_path,
        file_type=file_ext.lstrip('.'),
        material_type=material_type,
        extracted_text=extracted_text,
        user_id=current_user.id,
        course_id=course_id  # Can be None for miscellaneous materials
    )
    
    session.add(material)
    session.commit()
    session.refresh(material)
    
    # Update reading streak
    streak_service.update_streak(current_user.id, session)
    
    return material


@router.get("/", response_model=List[MaterialResponse])
async def list_materials(
    current_user: CurrentActiveUser = None,
    session: Session = Depends(get_session)
):
    """Get all materials for the current user."""
    stmt = select(Material).where(Material.user_id == current_user.id)
    materials = session.exec(stmt).all()
    return materials


@router.get("/{material_id}", response_model=MaterialResponse)
async def get_material(
    material_id: int,
    current_user: CurrentActiveUser = None,
    session: Session = Depends(get_session)
):
    """Get a specific material."""
    stmt = select(Material).where(
        Material.id == material_id,
        Material.user_id == current_user.id
    )
    material = session.exec(stmt).first()
    
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material not found"
        )
    
    return material


@router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material(
    material_id: int,
    current_user: CurrentActiveUser = None,
    session: Session = Depends(get_session)
):
    """Delete a material."""
    stmt = select(Material).where(
        Material.id == material_id,
        Material.user_id == current_user.id
    )
    material = session.exec(stmt).first()
    
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material not found"
        )
    
    # Delete file
    if os.path.exists(material.file_path):
        os.remove(material.file_path)
    
    session.delete(material)
    session.commit()
    
    return None
