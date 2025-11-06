from sqlmodel import Session
from app.core.database import database

def get_session():
    with Session(database) as session:
        yield session

