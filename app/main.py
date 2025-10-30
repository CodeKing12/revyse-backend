from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html
from database import create_tables
from routers import auth
import uvicorn

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(auth.router)

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)