from enum import Enum
from sqlmodel import Field, SQLModel, Relationship

class UserRole(str, Enum):
    USER = 0
    ADMIN = 1
    SUPERUSER = 2


class UserBase(SQLModel):
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)


class ProfileBase(UserBase):
    first_name: str
    last_name: str
    age: int


class User(UserBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    role: UserRole

    profile: "Profile" = Relationship(back_populates="user")


class Profile(ProfileBase, table=True):
    id: int | None = Field(default=None, primary_key=True)

    user_id: int = Field(foreign_key="user.id")
    user: User = Relationship(back_populates="profile")


class UserRegister(ProfileBase):
    pass