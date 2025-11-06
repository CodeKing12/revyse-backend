from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html
from app.core.database import create_tables
from app.auth import router
import uvicorn

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(router.router)

if __name__ == "__main__":
    uvicorn.run("app.core.main:app", reload=True)