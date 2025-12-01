from collections.abc import Generator
from pwdlib import PasswordHash
from pwdlib.hashers import argon2
from app.core.config import settings
from sqlmodel import Session, select, or_
from . import models
from datetime import datetime, timedelta, timezone
import jwt
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated
from fastapi import Depends, HTTPException, status
from app.core.dependencies import get_session

hasher = PasswordHash(hashers=[argon2.Argon2Hasher()])
oauth2_scheme = OAuth2PasswordBearer("/auth/token")
JWT_ALGORITHM = "HS256"

def encrypt_password(password: str):
    return hasher.hash(password, salt=settings.HASH_SALT)

def verify_password(password: str, hashed_password: str):
    return hasher.verify(password, hashed_password)

def get_user(username: str, session: Session):
    stmt = select(models.User).where(or_(models.User.username == username, models.User.email == username))
    return session.exec(stmt).first()

def authenticate_user(session: Session, username: str, password: str):
    user = get_user(username, session)
    print(user)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_auth_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=1)
    to_encode.update({"exp": expire})
    print("ENCODING: ", to_encode)
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)
def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], session: Session = Depends(get_session)):
    decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM])
    username = decoded.get("sub")
    if not username:
        raise credentials_exception
    return get_user(username, session)

def get_current_active_user(user: Annotated[models.User, Depends(get_current_user)]):
    if user.disabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return user

CurrentActiveUser = Annotated[models.User, Depends(get_current_active_user)]