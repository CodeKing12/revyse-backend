from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html
from app.core.database import create_tables
from app.auth import router as auth_router
from app.materials import router as materials_router
from app.materials import summaries_router
from app.materials import quizzes_router
from app.materials import flashcards_router
from app.materials import streaks_router
from app.materials import nudges_router
import uvicorn

# Create tables immediately when module is imported
# This ensures tables exist for TestClient as well
try:
    create_tables()
except Exception as e:
    print(f"Warning: Could not create tables on startup: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tables already created above
    yield

app = FastAPI(
    lifespan=lifespan,
    title="Revyse API",
    description="AI-powered study application backend",
    version="1.0.0"
)

# Include routers
app.include_router(auth_router.router)
app.include_router(materials_router.router)
app.include_router(summaries_router.router)
app.include_router(quizzes_router.router)
app.include_router(flashcards_router.router)
app.include_router(streaks_router.router)
app.include_router(nudges_router.router)

if __name__ == "__main__":
    uvicorn.run("app.core.main:app", reload=True)