from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
from fastapi.security import OAuth2PasswordRequestForm
from app.auth import models
from app.core.dependencies import get_session
from .dependencies import encrypt_password, authenticate_user, create_auth_token, CurrentActiveUser
from sqlmodel import Session, select
from datetime import timedelta

router = APIRouter(prefix="/auth")
ACCESS_TOKEN_EXPIRY_MINUTES = 60
REFRESH_TOKEN_EXPIRY_MINUTES = 720

@router.post("/register", response_model=models.UserRegisterResponse)
async def signup(reg_data: models.UserRegister, session: Session = Depends(get_session)):
    new_user = models.User(**reg_data.model_dump(exclude={"password"}), role=models.UserRole.USER, hashed_password=encrypt_password(reg_data.password))
    new_profile = models.Profile(**reg_data.model_dump(), user=new_user)

    session.add(new_profile)
    session.commit()
    return new_profile


@router.post("/token", response_model=models.UserLoginResponse)
async def login_user(login_form: Annotated[OAuth2PasswordRequestForm, Depends()], session: Session = Depends(get_session)):
    user = authenticate_user(session, login_form.username, login_form.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    token_val = {"sub": user.username, "id": user.id}
    access_token = create_auth_token(token_val, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRY_MINUTES))
    refresh_token = create_auth_token(token_val, expires_delta=timedelta(minutes=REFRESH_TOKEN_EXPIRY_MINUTES))

    return models.UserLoginResponse(access_token=access_token, refresh_token=refresh_token, token_type="bearer")


@router.get("/me", response_model=models.Profile)
async def get_user(current_user: CurrentActiveUser):
    print(current_user)
    return current_user.profile