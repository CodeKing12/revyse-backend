from sqlmodel import Session
from database import database
from collections.abc import Generator

def get_session():
    with Session(database) as session:
        yield session
