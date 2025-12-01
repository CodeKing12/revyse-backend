from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlmodel import Session, select
from typing import List, Optional
from app.core.dependencies import get_session
from app.auth.dependencies import CurrentActiveUser
from app.materials.models import (
    Course, CourseCreate, CourseUpdate, CourseResponse,
    Material, MaterialCreate, MaterialResponse, MaterialType,
    Summary, SummaryCreate, SummaryResponse,
    Quiz, QuizCreate, QuizResponse, Question, QuestionOption, QuestionResponse,
    FlashCard, FlashCardCreate, FlashCardResponse
)
# Use optimized services for cost savings
from app.services.optimized_file_service import file_processing_service
from app.services.unified_ai_service import ai_service
from app.services.streak_service import streak_service
from app.core.config import settings
import os
import shutil
from datetime import datetime

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.post("/", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    course: CourseCreate,
    current_user: CurrentActiveUser,
    session: Session = Depends(get_session)
):
    """Create a new course."""
    
    new_course = Course(
        title=course.title,
        description=course.description,
        user_id=current_user.id
    )
    
    session.add(new_course)
    session.commit()
    session.refresh(new_course)
    
    return new_course


@router.get("/", response_model=List[CourseResponse])
async def list_courses(
    current_user: CurrentActiveUser,
    session: Session = Depends(get_session)
):
    """Get all courses for the current user."""
    stmt = select(Course).where(Course.user_id == current_user.id)
    courses = session.exec(stmt).all()
    return courses


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: int,
    current_user: CurrentActiveUser,
    session: Session = Depends(get_session)
):
    """Get a specific course."""
    stmt = select(Course).where(
        Course.id == course_id,
        Course.user_id == current_user.id
    )
    course = session.exec(stmt).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    return course


@router.put("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: int,
    course_update: CourseUpdate,
    current_user: CurrentActiveUser,
    session: Session = Depends(get_session)
):
    """Update a course."""
    stmt = select(Course).where(
        Course.id == course_id,
        Course.user_id == current_user.id
    )
    course = session.exec(stmt).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    if course_update.title is not None:
        course.title = course_update.title
    if course_update.description is not None:
        course.description = course_update.description
    
    course.updated_at = datetime.utcnow()
    
    session.add(course)
    session.commit()
    session.refresh(course)
    
    return course


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: int,
    current_user: CurrentActiveUser,
    session: Session = Depends(get_session)
):
    """Delete a course."""
    stmt = select(Course).where(
        Course.id == course_id,
        Course.user_id == current_user.id
    )
    course = session.exec(stmt).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    session.delete(course)
    session.commit()
    
    return None


# Course Materials Endpoints
@router.post("/{course_id}/materials/upload", response_model=MaterialResponse, status_code=status.HTTP_201_CREATED)
async def upload_course_material(
    course_id: int,
    current_user: CurrentActiveUser,
    session: Session = Depends(get_session),
    file: UploadFile = File(...),
    title: str = None,
    description: str = None,
    material_type: MaterialType = MaterialType.OTHER
):
    """Upload a study material file to a course."""
    
    # Verify course belongs to user
    stmt = select(Course).where(
        Course.id == course_id,
        Course.user_id == current_user.id
    )
    course = session.exec(stmt).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Validate file type
    allowed_extensions = {'.pdf', '.docx', '.doc', '.txt'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_ext} not supported. Allowed types: {', '.join(allowed_extensions)}"
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
        course_id=course_id
    )
    
    session.add(material)
    session.commit()
    session.refresh(material)
    
    # Update reading streak
    streak_service.update_streak(current_user.id, session)
    
    return material


@router.get("/{course_id}/materials/", response_model=List[MaterialResponse])
async def list_course_materials(
    course_id: int,
    current_user: CurrentActiveUser,
    session: Session = Depends(get_session)
):
    """Get all materials for a course."""
    
    # Verify course belongs to user
    stmt = select(Course).where(
        Course.id == course_id,
        Course.user_id == current_user.id
    )
    course = session.exec(stmt).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    stmt = select(Material).where(Material.course_id == course_id)
    materials = session.exec(stmt).all()
    return materials


@router.get("/{course_id}/materials/{material_id}", response_model=MaterialResponse)
async def get_course_material(
    course_id: int,
    material_id: int,
    current_user: CurrentActiveUser,
    session: Session = Depends(get_session)
):
    """Get a specific material from a course."""
    
    # Verify course belongs to user
    stmt = select(Course).where(
        Course.id == course_id,
        Course.user_id == current_user.id
    )
    course = session.exec(stmt).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    stmt = select(Material).where(
        Material.id == material_id,
        Material.course_id == course_id
    )
    material = session.exec(stmt).first()
    
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material not found in this course"
        )
    
    return material


# Course Summaries
@router.post("/{course_id}/summaries/", response_model=SummaryResponse, status_code=status.HTTP_201_CREATED)
async def create_course_summary(
    course_id: int,
    data: SummaryCreate,
    current_user: CurrentActiveUser,
    session: Session = Depends(get_session)
):
    """Generate a summary for a course material."""
    
    if not ai_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured"
        )
    
    # Verify course belongs to user
    stmt = select(Course).where(
        Course.id == course_id,
        Course.user_id == current_user.id
    )
    course = session.exec(stmt).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Get material
    stmt = select(Material).where(
        Material.id == data.material_id,
        Material.course_id == course_id,
        Material.user_id == current_user.id
    )
    material = session.exec(stmt).first()
    
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material not found in this course"
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


@router.get("/{course_id}/summaries/", response_model=List[SummaryResponse])
async def list_course_summaries(
    course_id: int,
    current_user: CurrentActiveUser,
    session: Session = Depends(get_session)
):
    """Get all summaries for materials in a course."""
    
    # Verify course belongs to user
    stmt = select(Course).where(
        Course.id == course_id,
        Course.user_id == current_user.id
    )
    course = session.exec(stmt).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Get all materials for the course
    mat_stmt = select(Material).where(Material.course_id == course_id)
    materials = session.exec(mat_stmt).all()
    material_ids = [m.id for m in materials]
    
    if not material_ids:
        return []
    
    # Get summaries for these materials
    stmt = select(Summary).where(Summary.material_id.in_(material_ids))
    summaries = session.exec(stmt).all()
    return summaries


@router.get("/{course_id}/materials/{material_id}/summaries/", response_model=List[SummaryResponse])
async def list_course_material_summaries(
    course_id: int,
    material_id: int,
    current_user: CurrentActiveUser,
    session: Session = Depends(get_session)
):
    """Get all summaries for a specific course material."""
    
    # Verify course and material
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
    
    mat_stmt = select(Material).where(
        Material.id == material_id,
        Material.course_id == course_id
    )
    material = session.exec(mat_stmt).first()
    
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material not found in this course"
        )
    
    stmt = select(Summary).where(Summary.material_id == material_id)
    summaries = session.exec(stmt).all()
    return summaries


# Course Quizzes
@router.post("/{course_id}/quizzes/", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
async def create_course_quiz(
    course_id: int,
    data: QuizCreate,
    current_user: CurrentActiveUser,
    session: Session = Depends(get_session)
):
    """Generate a quiz from course materials using AI."""
    
    if not ai_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured"
        )
    
    # Verify course belongs to user
    stmt = select(Course).where(
        Course.id == course_id,
        Course.user_id == current_user.id
    )
    course = session.exec(stmt).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Get materials and combine their text
    materials_text = []
    for material_id in data.material_ids:
        stmt = select(Material).where(
            Material.id == material_id,
            Material.course_id == course_id,
            Material.user_id == current_user.id
        )
        material = session.exec(stmt).first()
        
        if not material:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Material {material_id} not found in this course"
            )
        
        if material.extracted_text:
            materials_text.append(material.extracted_text)
    
    if not materials_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No text content found in materials"
        )
    
    combined_text = "\n\n".join(materials_text)
    
    # Generate quiz questions using AI
    try:
        questions_data = ai_service.generate_quiz_questions(
            combined_text,
            num_questions=data.num_questions,
            difficulty=data.difficulty.value if data.difficulty else None,
            quiz_type=data.quiz_type.value
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate quiz: {str(e)}"
        )
    
    # Create quiz
    quiz = Quiz(
        title=data.title,
        description=data.description,
        quiz_type=data.quiz_type,
        user_id=current_user.id,
        time_limit_minutes=data.time_limit_minutes
    )
    session.add(quiz)
    session.commit()
    session.refresh(quiz)
    
    # Create questions and options
    from app.materials.models import QuestionType, DifficultyLevel
    questions_response = []
    for idx, q_data in enumerate(questions_data):
        question = Question(
            quiz_id=quiz.id,
            question_text=q_data.get("question_text", ""),
            question_type=QuestionType(q_data.get("question_type", "multiple_choice")),
            difficulty=q_data.get("difficulty", "medium"),
            points=q_data.get("points", 1),
            order=idx,
            explanation=q_data.get("explanation")
        )
        session.add(question)
        session.commit()
        session.refresh(question)
        
        options_list = []
        
        # Add options for multiple choice and true/false
        if question.question_type in [QuestionType.MULTIPLE_CHOICE, QuestionType.TRUE_FALSE]:
            options = q_data.get("options", [])
            
            # For true/false, create standard options if not provided
            if question.question_type == QuestionType.TRUE_FALSE and not options:
                correct_answer = q_data.get("correct_answer", "true").lower() == "true"
                options = [
                    {"text": "True", "is_correct": correct_answer},
                    {"text": "False", "is_correct": not correct_answer}
                ]
            
            for opt_idx, opt_data in enumerate(options):
                option = QuestionOption(
                    question_id=question.id,
                    option_text=opt_data.get("text", ""),
                    is_correct=opt_data.get("is_correct", False),
                    order=opt_idx
                )
                session.add(option)
                session.commit()
                session.refresh(option)
                options_list.append({
                    "id": option.id,
                    "text": option.option_text,
                    "is_correct": option.is_correct
                })
        
        questions_response.append(QuestionResponse(
            id=question.id,
            question_text=question.question_text,
            question_type=question.question_type,
            difficulty=question.difficulty,
            points=question.points,
            options=options_list if options_list else None
        ))
    
    return QuizResponse(
        id=quiz.id,
        title=quiz.title,
        description=quiz.description,
        quiz_type=quiz.quiz_type,
        time_limit_minutes=quiz.time_limit_minutes,
        questions=questions_response,
        created_at=quiz.created_at
    )


@router.get("/{course_id}/quizzes/", response_model=List[QuizResponse])
async def list_course_quizzes(
    course_id: int,
    current_user: CurrentActiveUser,
    session: Session = Depends(get_session)
):
    """Get all quizzes for a course."""
    
    # Verify course belongs to user
    stmt = select(Course).where(
        Course.id == course_id,
        Course.user_id == current_user.id
    )
    course = session.exec(stmt).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # For now, return all quizzes for the user
    # TODO: Link quizzes directly to courses in the future
    stmt = select(Quiz).where(Quiz.user_id == current_user.id)
    quizzes = session.exec(stmt).all()
    
    result = []
    for quiz in quizzes:
        questions_stmt = select(Question).where(Question.quiz_id == quiz.id)
        questions = session.exec(questions_stmt).all()
        
        questions_response = []
        for question in questions:
            options_stmt = select(QuestionOption).where(QuestionOption.question_id == question.id)
            options = session.exec(options_stmt).all()
            
            options_list = [
                {"id": opt.id, "text": opt.option_text, "is_correct": opt.is_correct}
                for opt in options
            ] if options else None
            
            questions_response.append(QuestionResponse(
                id=question.id,
                question_text=question.question_text,
                question_type=question.question_type,
                difficulty=question.difficulty,
                points=question.points,
                options=options_list
            ))
        
        result.append(QuizResponse(
            id=quiz.id,
            title=quiz.title,
            description=quiz.description,
            quiz_type=quiz.quiz_type,
            time_limit_minutes=quiz.time_limit_minutes,
            questions=questions_response,
            created_at=quiz.created_at
        ))
    
    return result


# Course Flashcards
@router.post("/{course_id}/flashcards/", response_model=List[FlashCardResponse], status_code=status.HTTP_201_CREATED)
async def create_course_flashcards(
    course_id: int,
    data: FlashCardCreate,
    current_user: CurrentActiveUser,
    session: Session = Depends(get_session)
):
    """Generate flashcards from course materials using AI."""
    
    if not ai_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured"
        )
    
    # Verify course belongs to user
    stmt = select(Course).where(
        Course.id == course_id,
        Course.user_id == current_user.id
    )
    course = session.exec(stmt).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Get materials and combine their text
    materials_text = []
    for material_id in data.material_ids:
        stmt = select(Material).where(
            Material.id == material_id,
            Material.course_id == course_id,
            Material.user_id == current_user.id
        )
        material = session.exec(stmt).first()
        
        if not material:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Material {material_id} not found in this course"
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


@router.get("/{course_id}/flashcards/", response_model=List[FlashCardResponse])
async def list_course_flashcards(
    course_id: int,
    current_user: CurrentActiveUser,
    session: Session = Depends(get_session)
):
    """Get all flashcards for materials in a course."""
    
    # Verify course belongs to user
    stmt = select(Course).where(
        Course.id == course_id,
        Course.user_id == current_user.id
    )
    course = session.exec(stmt).first()
    
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Get all materials for the course
    mat_stmt = select(Material).where(Material.course_id == course_id)
    materials = session.exec(mat_stmt).all()
    material_ids = [m.id for m in materials]
    
    if not material_ids:
        return []
    
    # Get flashcards for these materials
    stmt = select(FlashCard).where(
        FlashCard.material_id.in_(material_ids),
        FlashCard.user_id == current_user.id
    )
    flashcards = session.exec(stmt).all()
    return flashcards


@router.get("/{course_id}/materials/{material_id}/flashcards/", response_model=List[FlashCardResponse])
async def list_course_material_flashcards(
    course_id: int,
    material_id: int,
    current_user: CurrentActiveUser,
    session: Session = Depends(get_session)
):
    """Get all flashcards for a specific course material."""
    
    # Verify course and material
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
    
    mat_stmt = select(Material).where(
        Material.id == material_id,
        Material.course_id == course_id
    )
    material = session.exec(mat_stmt).first()
    
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material not found in this course"
        )
    
    stmt = select(FlashCard).where(
        FlashCard.material_id == material_id,
        FlashCard.user_id == current_user.id
    )
    flashcards = session.exec(stmt).all()
    return flashcards
