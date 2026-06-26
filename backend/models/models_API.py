import uuid
from enum import Enum
from datetime import datetime
from typing import List

from sqlmodel import SQLModel,Field
from pydantic import EmailStr

class ProjectAccess(Enum):
    participant="PARTICIPANT" 
    owner="OWNER"

class BaseUser(SQLModel):
    username: str|None =Field(max_length=255,min_length=1,default=None)
    email: EmailStr = Field(unique=True, max_length=255)


class UserCreate(BaseUser):
    password: str=Field(min_length=8,max_length=128)

class UserNewRegister(SQLModel):
    username: str|None =Field(min_length=1,max_length=128,default=None)
    email: EmailStr = Field(max_length=255)
    password: str=Field(min_length=8,max_length=128)
    repeat_password: str = Field(min_length=8,max_length=128)

class UserUpdates(SQLModel):
    username: str|None =Field(max_length=255,min_length=1,default=None)
    email: EmailStr = Field(max_length=255, default=None)

#Model with password received via API for recovery
class UserUpdatesAPI(SQLModel):
    password: str|None=Field(min_length=8,max_length=128, default=None)

class PublicUser(SQLModel):
    username: str|None =Field(min_length=1,max_length=128,default=None)
    user_id: uuid.UUID

class UpdatePassword(SQLModel):
    current_password: str =Field(min_length=8,max_length=128)
    new_password: str =Field(min_length=8,max_length=128)

class BaseProject(SQLModel):
    name: str =Field(min_length=1,max_length=255)
    description: str | None = None

class CreateProject(BaseProject):
    pass

class UpdateProject(BaseProject):
    name: str|None =Field(min_length=1,max_length=255,default=None)

class BaseDocument(SQLModel):
    filename: str=Field(nullable=False,max_length=255)
    s3_key: str=Field(max_length=500,unique=True)


class DocumentPublicByProject(SQLModel):
    filename: str
    doc_id: uuid.UUID
    uploaded_at: datetime

class ProjectPublicInfo(BaseProject):
    project_id: uuid.UUID
    updated_at: datetime


class ProjectPublic(ProjectPublicInfo):
    documents: List[DocumentPublicByProject]=[]

class ProjectsPublic(SQLModel):
    projects: List[ProjectPublic]
    count_projects: int

class DocumentPublic(DocumentPublicByProject):
    project_id: uuid.UUID

class DocumentDownloadResponse(SQLModel):
    url_to_download: str

class DocumentsPublic(SQLModel):
    documents: List[DocumentPublicByProject]

class UploadDocuments(SQLModel):
      documents:List[BaseDocument]=[]

class Message(SQLModel):
    message: str













