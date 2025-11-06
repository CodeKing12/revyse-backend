from enum import Enum
from sqlmodel import Field, SQLModel, Relationship

class UserRole(str, Enum):
    USER = 0
    ADMIN = 1
    SUPERUSER = 2


class AcademicLevel(str, Enum):
    COLLEGE = 0
    UNIVERSITY = 1
    MASTERS = 2
    PROFESSOR = 3


class UserBase(SQLModel):
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)


class ProfileBase(UserBase):
    first_name: str
    last_name: str
    age: int
    academic_level: AcademicLevel | None = Field(default=None)


class User(UserBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    role: UserRole
    hashed_password: str = Field()
    disabled: bool = Field(default=False)

    profile: "Profile" = Relationship(back_populates="user")


class Profile(ProfileBase, table=True):
    id: int | None = Field(default=None, primary_key=True)

    user_id: int = Field(foreign_key="user.id")
    user: User = Relationship(back_populates="profile")


class UserRegister(ProfileBase):
    password: str = Field(min_length=4)

class UserRegisterResponse(ProfileBase):
    pass


class UserLoginResponse(SQLModel):
    access_token: str
    refresh_token: str
    token_type: str
