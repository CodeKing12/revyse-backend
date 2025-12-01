from enum import Enum
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime
from typing import Optional, List


class MaterialType(str, Enum):
    LECTURE_NOTES = "lecture_notes"
    STUDENT_NOTES = "student_notes"
    TEXTBOOK = "textbook"
    SLIDES = "slides"
    OTHER = "other"


class Course(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: Optional[str] = None
    user_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    materials: List["Material"] = Relationship(back_populates="course")


class Material(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: Optional[str] = None
    file_path: str
    file_type: str  # pdf, docx, txt, etc
    material_type: MaterialType
    extracted_text: Optional[str] = None
    user_id: int = Field(foreign_key="user.id")
    course_id: Optional[int] = Field(default=None, foreign_key="course.id")  # Can be None for miscellaneous materials
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    course: Optional[Course] = Relationship(back_populates="materials")
    summaries: List["Summary"] = Relationship(back_populates="material")
    flashcards: List["FlashCard"] = Relationship(back_populates="material")


class Summary(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    material_id: int = Field(foreign_key="material.id")
    content: str
    summary_type: str = "general"  # general, detailed, brief
    user_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    material: Material = Relationship(back_populates="summaries")


class QuestionType(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"


class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuizType(str, Enum):
    QUIZ = "quiz"
    TEST = "test"
    EXAM = "exam"
    PRACTICE = "practice"


class Quiz(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: Optional[str] = None
    quiz_type: QuizType
    user_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    time_limit_minutes: Optional[int] = None

    # Relationships
    questions: List["Question"] = Relationship(back_populates="quiz")
    submissions: List["QuizSubmission"] = Relationship(back_populates="quiz")


class Question(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    quiz_id: int = Field(foreign_key="quiz.id")
    question_text: str
    question_type: QuestionType
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    points: int = 1
    order: int = 0
    explanation: Optional[str] = None

    # Relationships
    quiz: Quiz = Relationship(back_populates="questions")
    options: List["QuestionOption"] = Relationship(back_populates="question")
    answers: List["Answer"] = Relationship(back_populates="question")


class QuestionOption(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    question_id: int = Field(foreign_key="question.id")
    option_text: str
    is_correct: bool = False
    order: int = 0

    # Relationships
    question: Question = Relationship(back_populates="options")


class QuizSubmission(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    quiz_id: int = Field(foreign_key="quiz.id")
    user_id: int = Field(foreign_key="user.id")
    score: Optional[float] = None
    max_score: Optional[float] = None
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    time_taken_minutes: Optional[int] = None

    # Relationships
    quiz: Quiz = Relationship(back_populates="submissions")
    answers: List["Answer"] = Relationship(back_populates="submission")


class Answer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    submission_id: int = Field(foreign_key="quizsubmission.id")
    question_id: int = Field(foreign_key="question.id")
    answer_text: Optional[str] = None
    selected_option_id: Optional[int] = Field(default=None, foreign_key="questionoption.id")
    is_correct: Optional[bool] = None
    points_earned: float = 0

    # Relationships
    submission: QuizSubmission = Relationship(back_populates="answers")
    question: Question = Relationship(back_populates="answers")


class FlashCard(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    material_id: Optional[int] = Field(default=None, foreign_key="material.id")
    user_id: int = Field(foreign_key="user.id")
    front: str  # Question or term
    back: str  # Answer or definition
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_reviewed: Optional[datetime] = None
    review_count: int = 0
    mastery_level: int = 0  # 0-5, higher is more mastered

    # Relationships
    material: Optional[Material] = Relationship(back_populates="flashcards")


class ReadingStreak(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True)
    current_streak: int = 0
    longest_streak: int = 0
    last_activity_date: Optional[datetime] = None
    total_reading_days: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DailyNudge(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    message: str
    nudge_type: str = "daily"  # daily, orientation, reminder, motivation
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    is_read: bool = False
    scheduled_for: Optional[datetime] = None


# Pydantic models for API requests/responses
class CourseCreate(SQLModel):
    title: str
    description: Optional[str] = None


class CourseUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None


class CourseResponse(SQLModel):
    id: int
    title: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime


class MaterialCreate(SQLModel):
    title: str
    description: Optional[str] = None
    material_type: MaterialType
    course_id: Optional[int] = None  # Optional course assignment


class MaterialResponse(SQLModel):
    id: int
    title: str
    description: Optional[str]
    file_type: str
    material_type: MaterialType
    course_id: Optional[int]
    created_at: datetime


class SummaryCreate(SQLModel):
    material_id: int
    summary_type: str = "general"


class SummaryResponse(SQLModel):
    id: int
    material_id: int
    content: str
    summary_type: str
    created_at: datetime


class QuizCreate(SQLModel):
    title: str
    description: Optional[str] = None
    quiz_type: QuizType
    material_ids: List[int]
    num_questions: int = 10
    difficulty: Optional[DifficultyLevel] = None
    time_limit_minutes: Optional[int] = None


class QuestionResponse(SQLModel):
    id: int
    question_text: str
    question_type: QuestionType
    difficulty: DifficultyLevel
    points: int
    options: Optional[List[dict]] = None


class QuizResponse(SQLModel):
    id: int
    title: str
    description: Optional[str]
    quiz_type: QuizType
    time_limit_minutes: Optional[int]
    questions: List[QuestionResponse]
    created_at: datetime


class QuizSubmissionCreate(SQLModel):
    quiz_id: int
    answers: List[dict]  # [{"question_id": 1, "answer_text": "...", "selected_option_id": 1}]


class QuizSubmissionResponse(SQLModel):
    id: int
    quiz_id: int
    score: Optional[float]
    max_score: Optional[float]
    submitted_at: datetime
    time_taken_minutes: Optional[int]


class FlashCardCreate(SQLModel):
    material_ids: List[int]
    num_cards: int = 20


class FlashCardResponse(SQLModel):
    id: int
    front: str
    back: str
    difficulty: DifficultyLevel
    mastery_level: int
    review_count: int


class ReadingStreakResponse(SQLModel):
    current_streak: int
    longest_streak: int
    last_activity_date: Optional[datetime]
    total_reading_days: int


class DailyNudgeResponse(SQLModel):
    id: int
    message: str
    nudge_type: str
    sent_at: datetime
    is_read: bool
