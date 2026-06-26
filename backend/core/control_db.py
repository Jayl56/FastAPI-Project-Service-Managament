from collections.abc import Generator
import uuid
from typing import Annotated
from fastapi import Depends,HTTPException,status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt.exceptions import InvalidTokenError,ExpiredSignatureError
from pydantic import ValidationError
from backend.models.models_API import ProjectAccess
import backend.models.models_db as db_model
from sqlmodel import Session, SQLModel,create_engine
from backend.core.security import ALGORITHM,TokenPayload
from backend.core.app_config import settings
import backend.crud_db as crud_db


engine = create_engine(str(settings.sqlalchemy_database_uri))
def init_db()->None:
    SQLModel.metadata.create_all(engine)

def get_db_session()->Generator[Session,None,None]:
    with Session(engine) as session:
        yield session

SessionDep=Annotated[Session,Depends(get_db_session)]

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"auth/login/access-token")
TokenDep=Annotated[str,Depends(reusable_oauth2)]

def get_current_user(session:SessionDep,token:TokenDep)->db_model.User:
    try:
        payload=jwt.decode(token,settings.SECRET_KEY,algorithms=[ALGORITHM])
        token_info=TokenPayload(**payload)
        try:
            user_id = uuid.UUID(token_info.sub)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Could not validate credentials"
            )
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Token has expired, please log in again")
    except (InvalidTokenError,ValidationError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Could not validate credentials")
    user=session.get(db_model.User,token_info.sub)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User does not exist")
    return user

CurrentUser=Annotated[db_model.User,Depends(get_current_user)]

def get_actual_project(session:SessionDep,project_id:uuid.UUID)->db_model.Project:
    project = crud_db.get_project_by_id(db_session=session, project_id=project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project does not exist.")
    return project

ActiveProject=Annotated[db_model.Project,Depends(get_actual_project)]

def is_member(session:SessionDep,project:ActiveProject,current_user:CurrentUser)->db_model.ProjectMember:
    member = crud_db.authenticate_project_member(db_session=session, project_id=project.project_id,user_id=current_user.user_id)
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not enough permissions.You are neither a participant nor an owner of this project.")
    return member

ActiveMember=Annotated[db_model.ProjectMember,Depends(is_member)]

def is_owner(member:ActiveMember)->db_model.ProjectMember:
    if member.role!=ProjectAccess.owner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Not enough permissions, you are not the project's owner.")
    return member

ProjectOwner=Annotated[db_model.ProjectMember,Depends(is_owner)]

def get_actual_document(session:SessionDep,doc_id:uuid.UUID,current_user:CurrentUser)->db_model.Document:
    document = crud_db.get_document_by_id(db_session=session, document_id=doc_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document does not exist.")
    if not crud_db.authenticate_project_member(
            db_session=session,
            project_id=document.project_id,
            user_id=current_user.user_id
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You are not a member of the project this document belongs to.")
    return document

AvailableDoc=Annotated[db_model.Document,Depends(get_actual_document)]












