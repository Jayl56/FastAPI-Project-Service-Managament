from datetime import datetime,timezone
import uuid
from typing import List,Optional
from pydantic import EmailStr
from backend.models.models_API import ProjectAccess
from sqlalchemy import Text,Column,DateTime
from sqlmodel import (
SQLModel,
Field,
Relationship,
)


class ProjectMember(SQLModel,table=True):
    __tablename__ = "project_members"
    project_id: uuid.UUID =Field(
        foreign_key="projects.project_id",
        primary_key=True,ondelete="CASCADE")
    user_id: uuid.UUID=Field(
        foreign_key="users.user_id",
        primary_key=True,ondelete="CASCADE")
    role: ProjectAccess


class User(SQLModel,table=True):
    __tablename__ = "users"
    user_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True)
    username: str =Field(
        min_length=1,
        max_length=255,
        default=None)
    email: EmailStr = Field(
        unique=True,
        max_length=255)
    hash_password: str

    projects: List["Project"] = Relationship(
        back_populates="members",
        link_model=ProjectMember
    )

class Project (SQLModel,table=True):
    __tablename__ = "projects"
    project_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True)
    name: str = Field(
        min_length=1,
        max_length=100)
    description: str | None = Field(
        sa_type=Text,
        default=None)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
    )
    members: List["User"] = Relationship(
        back_populates="projects",
        link_model=ProjectMember
    )
    documents: List["Document"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all,delete-orphan"}
    )

class Document(SQLModel,table=True):
    __tablename__ = "documents"
    doc_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True)
    project_id: uuid.UUID =Field(
        foreign_key="projects.project_id",
        ondelete="CASCADE")
    uploaded_by: uuid.UUID = Field(
        foreign_key="users.user_id")
    filename: str=Field(
        nullable=False,
        max_length=255)
    s3_key: str|None =Field(
        max_length=500,
        unique=True)
    uploaded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
    )
    project:Optional["Project"] = Relationship(
        back_populates="documents",
    )

