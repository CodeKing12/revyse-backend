from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List
from app.core.dependencies import get_session
from app.auth.dependencies import CurrentActiveUser
from app.materials.models import (
    Material, Quiz, Question, QuestionOption, QuizSubmission, Answer,
    QuizCreate, QuizResponse, QuestionResponse, QuizSubmissionCreate,
    QuizSubmissionResponse, QuestionType
)
# Use optimized AI service for cost savings
from app.services.unified_ai_service import ai_service
from app.services.streak_service import streak_service

router = APIRouter(prefix="/quizzes", tags=["Quizzes"])


@router.post("/", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
async def create_quiz(
    data: QuizCreate,
    current_user: CurrentActiveUser = None,
    session: Session = Depends(get_session)
):
    """Generate a quiz from materials using AI."""
    
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


@router.get("/", response_model=List[QuizResponse])
async def list_quizzes(
    current_user: CurrentActiveUser = None,
    session: Session = Depends(get_session)
):
    """Get all quizzes for the current user."""
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


@router.get("/{quiz_id}", response_model=QuizResponse)
async def get_quiz(
    quiz_id: int,
    current_user: CurrentActiveUser = None,
    session: Session = Depends(get_session)
):
    """Get a specific quiz with questions."""
    stmt = select(Quiz).where(
        Quiz.id == quiz_id,
        Quiz.user_id == current_user.id
    )
    quiz = session.exec(stmt).first()
    
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    questions_stmt = select(Question).where(Question.quiz_id == quiz.id)
    questions = session.exec(questions_stmt).all()
    
    questions_response = []
    for question in questions:
        options_stmt = select(QuestionOption).where(QuestionOption.question_id == question.id)
        options = session.exec(options_stmt).all()
        
        # Don't expose correct answers when taking quiz
        options_list = [
            {"id": opt.id, "text": opt.option_text}
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
    
    return QuizResponse(
        id=quiz.id,
        title=quiz.title,
        description=quiz.description,
        quiz_type=quiz.quiz_type,
        time_limit_minutes=quiz.time_limit_minutes,
        questions=questions_response,
        created_at=quiz.created_at
    )


@router.post("/submit", response_model=QuizSubmissionResponse, status_code=status.HTTP_201_CREATED)
async def submit_quiz(
    data: QuizSubmissionCreate,
    current_user: CurrentActiveUser = None,
    session: Session = Depends(get_session)
):
    """Submit answers for a quiz and get graded."""
    
    # Get quiz
    stmt = select(Quiz).where(
        Quiz.id == data.quiz_id,
        Quiz.user_id == current_user.id
    )
    quiz = session.exec(stmt).first()
    
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    # Create submission
    submission = QuizSubmission(
        quiz_id=data.quiz_id,
        user_id=current_user.id
    )
    session.add(submission)
    session.commit()
    session.refresh(submission)
    
    # Grade answers
    total_points = 0
    earned_points = 0
    
    for answer_data in data.answers:
        question_id = answer_data.get("question_id")
        
        # Get question
        q_stmt = select(Question).where(Question.id == question_id)
        question = session.exec(q_stmt).first()
        
        if not question:
            continue
        
        total_points += question.points
        
        is_correct = False
        points = 0
        
        if question.question_type in [QuestionType.MULTIPLE_CHOICE, QuestionType.TRUE_FALSE]:
            selected_option_id = answer_data.get("selected_option_id")
            
            # Get the selected option
            opt_stmt = select(QuestionOption).where(QuestionOption.id == selected_option_id)
            selected_option = session.exec(opt_stmt).first()
            
            if selected_option and selected_option.is_correct:
                is_correct = True
                points = question.points
                earned_points += points
            
            answer = Answer(
                submission_id=submission.id,
                question_id=question.id,
                selected_option_id=selected_option_id,
                is_correct=is_correct,
                points_earned=points
            )
        else:
            # For short answer and essay, store the answer text
            # In a real application, you might want to use AI to grade these
            answer = Answer(
                submission_id=submission.id,
                question_id=question.id,
                answer_text=answer_data.get("answer_text", ""),
                is_correct=None,  # Requires manual grading
                points_earned=0
            )
        
        session.add(answer)
    
    # Update submission with score
    submission.score = earned_points
    submission.max_score = total_points
    
    session.add(submission)
    session.commit()
    session.refresh(submission)
    
    # Update reading streak
    streak_service.update_streak(current_user.id, session)
    
    return submission


@router.get("/submissions/{submission_id}", response_model=QuizSubmissionResponse)
async def get_submission(
    submission_id: int,
    current_user: CurrentActiveUser = None,
    session: Session = Depends(get_session)
):
    """Get details of a quiz submission."""
    stmt = select(QuizSubmission).where(
        QuizSubmission.id == submission_id,
        QuizSubmission.user_id == current_user.id
    )
    submission = session.exec(stmt).first()
    
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )
    
    return submission


@router.delete("/{quiz_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quiz(
    quiz_id: int,
    current_user: CurrentActiveUser = None,
    session: Session = Depends(get_session)
):
    """Delete a quiz."""
    stmt = select(Quiz).where(
        Quiz.id == quiz_id,
        Quiz.user_id == current_user.id
    )
    quiz = session.exec(stmt).first()
    
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    session.delete(quiz)
    session.commit()
    
    return None
