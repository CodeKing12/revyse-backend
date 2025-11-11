# Revyse Backend - AI Study Application

An AI-powered study application backend built with FastAPI that helps students across all educational levels manage their learning materials and improve their study habits.

## Features

### 1. Material Management
- **Upload Study Materials**: Support for PDF, DOCX, and TXT files
- **Automatic Text Extraction**: Extract text content from uploaded files
- **Material Organization**: Categorize materials as lecture notes, student notes, textbooks, slides, or other

### 2. AI-Powered Summaries
- **Generate Summaries**: Create AI-generated summaries of uploaded materials
- **Multiple Summary Types**: 
  - General summaries for quick overview
  - Brief summaries for quick reference
  - Detailed summaries for in-depth study
- **Persistent Storage**: Save and retrieve summaries for future reference

### 3. Quiz, Test & Exam Generation
- **AI-Generated Assessments**: Automatically generate quizzes from study materials
- **Multiple Question Types**:
  - Multiple Choice Questions (MCQ)
  - True/False Questions
  - Short Answer Questions
  - Essay Questions
- **Difficulty Levels**: Easy, Medium, and Hard questions
- **Assessment Types**: Quiz, Test, Exam, and Practice modes
- **Automatic Grading**: Instant feedback on multiple choice and true/false questions
- **Time Limits**: Optional time constraints for assessments

### 4. Flashcard System
- **AI-Generated Flashcards**: Create flashcards from study materials
- **Spaced Repetition**: Track review count and mastery level
- **Practice Mode**: Review flashcards with quality ratings
- **Progress Tracking**: Monitor improvement over time

### 5. Reading Streak Tracking
- **Daily Streak Counter**: Track consecutive days of study activity
- **Longest Streak**: Record personal best streaks
- **Activity Recording**: Automatic updates when using the platform
- **Streak Status**: Real-time notifications about streak status

### 6. Daily Nudges & Orientation
- **Daily Motivation**: AI-generated motivational messages
- **Orientation Messages**: Personalized onboarding for new users
- **Context-Aware**: Nudges based on user's current streak and activity
- **Read/Unread Tracking**: Mark messages as read

## Technology Stack

- **Framework**: FastAPI 0.120.2
- **Database**: SQLModel with PostgreSQL/SQLite support
- **AI Integration**: OpenRouter (supports multiple AI models)
  - **Default Model**: Google Gemini Flash 1.5 (cost-effective)
  - **Supported Models**: OpenAI GPT-4, Anthropic Claude, Google Gemini, and 100+ other models
  - **Switchable**: Change AI models anytime via configuration
- **File Processing**: 
  - PyPDF2 for PDF text extraction
  - python-docx for DOCX text extraction
- **Authentication**: JWT tokens with Argon2 password hashing
- **API Documentation**: Auto-generated OpenAPI (Swagger) documentation

## API Endpoints

### Authentication
- `POST /auth/register` - Register a new user
- `POST /auth/token` - Login and get access token
- `GET /auth/me` - Get current user profile

### Courses (Primary Structure)
- `POST /courses/` - Create a new course
- `GET /courses/` - List all courses
- `GET /courses/{id}` - Get a specific course
- `PUT /courses/{id}` - Update a course
- `DELETE /courses/{id}` - Delete a course

### Course Materials
- `POST /courses/{id}/materials/upload` - Upload material to a course
- `GET /courses/{id}/materials/` - List all materials in a course
- `GET /courses/{id}/materials/{material_id}` - Get specific course material

### Course Summaries
- `POST /courses/{id}/summaries/` - Generate summary for course material
- `GET /courses/{id}/summaries/` - List all summaries for course materials
- `GET /courses/{id}/materials/{material_id}/summaries/` - Get summaries for specific material

### Course Quizzes
- `POST /courses/{id}/quizzes/` - Generate quiz from course materials
- `GET /courses/{id}/quizzes/` - List all quizzes for a course
- `POST /quizzes/submit` - Submit quiz answers and get graded
- `GET /quizzes/submissions/{id}` - Get submission details

### Course Flashcards
- `POST /courses/{id}/flashcards/` - Generate flashcards from course materials
- `GET /courses/{id}/flashcards/` - List all flashcards for course materials
- `GET /courses/{id}/materials/{material_id}/flashcards/` - Get flashcards for specific material
- `POST /flashcards/{id}/review` - Record a flashcard review

### Reading Streaks
- `GET /streaks/` - Get current reading streak
- `POST /streaks/record` - Manually record reading activity
- `GET /streaks/status` - Check streak status and risk level

### Daily Nudges
- `POST /nudges/generate` - Generate a new nudge
- `GET /nudges/` - List all nudges
- `GET /nudges/today` - Get today's nudge (auto-generates if needed)
- `PUT /nudges/{id}/read` - Mark a nudge as read

## Installation

1. Clone the repository:
```bash
git clone https://github.com/CodeKing12/revyse-backend.git
cd revyse-backend
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables (create a `.env` file):
```env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=revyse
DB_USER=your_username
DB_PASSWORD=your_password

# Security
SECRET_KEY=your-secret-key-here
HASH_SALT=your-salt-here

# AI Service - Using OpenRouter for multi-model support
OPENROUTER_API_KEY=your-openrouter-api-key

# AI Model Selection (examples)
AI_MODEL=google/gemini-flash-1.5  # Default (cost-effective)
# AI_MODEL=openai/gpt-4o-mini
# AI_MODEL=anthropic/claude-3-haiku

# File Storage
UPLOAD_DIR=uploads
```

4. Run the application:
```bash
python -m app.core.main
```

Or using uvicorn directly:
```bash
uvicorn app.core.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the application is running, visit:
- **Interactive API docs (Swagger UI)**: http://localhost:8000/docs
- **Alternative API docs (ReDoc)**: http://localhost:8000/redoc
- **OpenAPI schema**: http://localhost:8000/openapi.json

## Usage Example

### 1. Register and Login
```python
import requests

# Register
response = requests.post("http://localhost:8000/auth/register", json={
    "username": "student1",
    "email": "student@example.com",
    "password": "securepassword",
    "first_name": "John",
    "last_name": "Doe",
    "age": 20,
    "academic_level": "university"
})

# Login
response = requests.post("http://localhost:8000/auth/token", data={
    "username": "student1",
    "password": "securepassword"
})
token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
```

### 2. Upload Material
```python
# Upload a PDF file
with open("lecture_notes.pdf", "rb") as f:
    files = {"file": f}
    data = {
        "title": "Introduction to Physics",
        "description": "Chapter 1 lecture notes",
        "material_type": "lecture_notes"
    }
    response = requests.post(
        "http://localhost:8000/materials/upload",
        files=files,
        data=data,
        headers=headers
    )
material_id = response.json()["id"]
```

### 3. Generate Summary
```python
response = requests.post(
    "http://localhost:8000/summaries/",
    json={
        "material_id": material_id,
        "summary_type": "general"
    },
    headers=headers
)
summary = response.json()
print(summary["content"])
```

### 4. Generate Quiz
```python
response = requests.post(
    "http://localhost:8000/quizzes/",
    json={
        "title": "Physics Chapter 1 Quiz",
        "quiz_type": "quiz",
        "material_ids": [material_id],
        "num_questions": 10,
        "difficulty": "medium"
    },
    headers=headers
)
quiz = response.json()
```

### 5. Generate Flashcards
```python
response = requests.post(
    "http://localhost:8000/flashcards/",
    json={
        "material_ids": [material_id],
        "num_cards": 20
    },
    headers=headers
)
flashcards = response.json()
```

### 6. Track Reading Streak
```python
# Get current streak
response = requests.get("http://localhost:8000/streaks/", headers=headers)
streak = response.json()
print(f"Current streak: {streak['current_streak']} days")

# Record activity
response = requests.post("http://localhost:8000/streaks/record", headers=headers)
```

## Database Schema

The application uses SQLModel (built on SQLAlchemy) with the following main tables:

- **user**: User accounts and authentication
- **profile**: User profile information
- **material**: Uploaded study materials
- **summary**: AI-generated summaries
- **quiz**: Quiz/test/exam definitions
- **question**: Individual quiz questions
- **questionoption**: Multiple choice options
- **quizsubmission**: User quiz submissions
- **answer**: Individual answers to questions
- **flashcard**: Study flashcards
- **readingstreak**: User reading streaks
- **dailynudge**: Motivational messages

## Future Enhancements

As mentioned in the project requirements, future implementations will include:

1. **Image Generation**: Create visual summary cards and charts
2. **Video Generation**: Generate illustrated explanations
3. **Audio Generation**: Create audiobooks and audio explanations
4. **AI Assistant**: Integration with calls and group study sessions
5. **Advanced Analytics**: Detailed learning progress tracking
6. **Collaborative Features**: Group study and shared materials
7. **Mobile Applications**: iOS and Android apps

## Architecture

The codebase follows a modular architecture:

```
app/
├── auth/              # Authentication and user management
├── core/              # Core configuration and database setup
├── materials/         # All material-related routers
│   ├── router.py             # Material upload and management
│   ├── summaries_router.py   # Summary generation
│   ├── quizzes_router.py     # Quiz generation and submission
│   ├── flashcards_router.py  # Flashcard management
│   ├── streaks_router.py     # Reading streak tracking
│   └── nudges_router.py      # Daily nudges
├── services/          # Business logic services
│   ├── ai_service.py         # OpenAI integration
│   ├── file_service.py       # File processing
│   └── streak_service.py     # Streak calculations
└── models/            # Database model imports
```

## Scalability Considerations

The application is designed with scalability in mind:

1. **Stateless API**: All endpoints are stateless, supporting horizontal scaling
2. **Database Connection Pooling**: Efficient database connection management
3. **Async Support**: FastAPI's async capabilities for concurrent requests
4. **File Storage**: Configurable to use local or cloud storage (S3, etc.)
5. **Caching**: Ready for Redis integration for session and data caching
6. **Microservices Ready**: Modular design allows easy service extraction
7. **Cloud Deployment**: Compatible with Docker, Kubernetes, and cloud platforms

## Security Features

- **Password Hashing**: Argon2 algorithm for secure password storage
- **JWT Authentication**: Secure token-based authentication
- **Input Validation**: Pydantic models for request validation
- **SQL Injection Protection**: SQLModel/SQLAlchemy ORM
- **File Upload Validation**: Type and size restrictions
- **Rate Limiting Ready**: Structure supports rate limiting middleware

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new features
5. Submit a pull request

## License

[Add your license information here]

## Support

For issues, questions, or contributions, please contact [your contact information].

---

Built with ❤️ for students everywhere.
