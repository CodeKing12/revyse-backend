from fastapi import APIRouter, Depends
from models import auth
from dependencies import get_session
from sqlmodel import Session, select

router = APIRouter(prefix="/auth")

@router.put("/register")
async def signup(reg_data: auth.UserRegister, session: Session = Depends(get_session)):
    new_user = auth.Profile(**reg_data.model_dump())

    session.add(new_user)
    session.commit()
    return new_user
    print("All Users", session.exec(select(auth.User)).all())
