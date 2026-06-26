from datetime import datetime,timezone
import uuid
from typing import List
from backend.core.security import verify_password,get_hash_password
from pydantic import EmailStr
from backend.models.models_db import User, ProjectMember,Project,Document
from sqlmodel import Session,select,col
from backend.models.models_API import (
    UserCreate, CreateProject, ProjectAccess, UpdateProject,UploadDocuments, UserUpdatesAPI
)



def create_user(*,db_session: Session,user_create:UserCreate)->User:
    """Create a new user from UserCreate SQLModel input."""
    user_obj= User.model_validate(user_create,update={"hash_password":get_hash_password(user_create.password)})
    db_session.add(user_obj)
    db_session.commit()
    return user_obj


def get_user_by_id(*,db_session: Session,user_id:uuid.UUID)->User:
    """Retrieve user by id."""
    session_user=db_session.get(User, user_id)
    return session_user


def get_user_by_email(*,db_session: Session,email:EmailStr)->User|None:
    """Retrieve user by email."""
    statement = select(User).where(User.email == email)
    return db_session.exec(statement).first()


DUMMY_HASH= "$argon2id$v=19$m=65536,t=3,p=4$YjNhY2Y5MjEzN2Q0NTYxZA$0tA6Q6A7W7b7nM4xQ6V4wV8mQ5h5mXk5zQk0zX5lR8Q"


def authenticate_user(*,db_session:Session,email:str,password:str)->User|None:
    """User authentication by email and password checking."""
    user_db=get_user_by_email(db_session=db_session,email=email)
    if not user_db:
        verify_password(password,DUMMY_HASH)
        return None
    verified=verify_password(password,user_db.hash_password)
    if not verified:
        return None
    return user_db

def update_user_password(*,db_session:Session,user:User,user_new_info:UserUpdatesAPI)->None:
    user_info=user_new_info.model_dump(exclude_unset=True)
    extra_info={}
    if "password" in user_info:
        new_password=user_info["password"]
        hashed_password=get_hash_password(new_password)
        extra_info["hash_password"]=hashed_password
    user.sqlmodel_update(user_info,update=extra_info)
    db_session.add(user)
    db_session.commit()


def authenticate_project_member(*,db_session:Session,project_id:uuid.UUID,user_id:uuid.UUID)->ProjectMember|None:
    """Authenticate project member by user_id and project_id."""
    member=db_session.get(ProjectMember,(project_id,user_id))
    return member


def create_project_member(*, db_session:Session, project_id:uuid.UUID, user_id:uuid.UUID, member_type:ProjectAccess)->None:
    """Project member creation by specifying user_id and project_id with role assignation."""
    new_member=ProjectMember(
        project_id=project_id,
        user_id=user_id,
        role=member_type)
    db_session.add(new_member)
    db_session.commit()

def create_project(*,db_session: Session,new_project:CreateProject,owner_id:uuid.UUID)->Project:
    """Create a new project from CreateProject SQLModel and owner_id."""
    valid_project=Project.model_validate(new_project)
    db_session.add(valid_project)

    db_session.flush() # Issues necessary SQL statements and update ID map, but does not commit the transaction.#

    create_project_member(db_session=db_session, project_id=valid_project.project_id, user_id=owner_id,
                          member_type=ProjectAccess.owner)

    db_session.commit()
    return valid_project

def get_available_projects_user_role(*, db_session:Session, user_id:uuid.UUID, role: ProjectAccess | None=None, limit:int=10)->List[Project]:
    """Retrieves a list of projects available for a given user_id and the desired number (limit) of records.
    If it is a role defined, it filters according to it."""
    statement=(
        select(Project)
        .join(ProjectMember)
        .where(ProjectMember.user_id == user_id)
    )

    if role:
        statement=statement.where(ProjectMember.role==role)

    statement=statement.order_by(col(Project.updated_at).desc()).limit(limit)

    projects=db_session.exec(statement).all()

    return projects

def get_project_owner(*,db_session:Session, project_id:uuid.UUID)->User|None:
    statement=(
        select(ProjectMember).
        where(ProjectMember.project_id==project_id,ProjectMember.role=="owner")
    )
    member=db_session.exec(statement).one()
    user_owner=db_session.get(User,member.user_id)
    return user_owner

def get_project_by_id(*,db_session:Session, project_id:uuid.UUID)->Project|None:
    """Retrieves a project by its id."""
    project=db_session.get(Project,project_id)
    return project


def update_project_details(*,db_session:Session, original_project:Project, info_to_update:UpdateProject)->Project:
    """Updates project details (name,description)."""
    update_data = info_to_update.model_dump(
        exclude_unset=True
    )

    if update_data:
        original_project.sqlmodel_update(update_data)
        original_project.updated_at = datetime.now(timezone.utc)
        db_session.commit()
        db_session.refresh(original_project)

    return original_project



def upload_documents_for_project(*,db_session:Session,user_id:uuid.UUID,project_id:uuid.UUID,upload_docs:UploadDocuments)->None:
    """Uploads documents to be associated
    with a project and returns all the project documents."""

    if upload_docs.documents:
        documents=[]
        for doc in upload_docs.documents:

            new_doc=Document(
                 filename=doc.filename,
                 project_id=project_id,
                 uploaded_by=user_id,
                 s3_key=doc.s3_key,
            )
            documents.append(new_doc)
        db_session.add_all(documents)
        project=get_project_by_id(db_session=db_session,project_id=project_id)
        if project:
            project.updated_at=datetime.now(timezone.utc)
        db_session.commit()


def get_document_by_id(*,db_session:Session, document_id:uuid.UUID)->Document|None:
    """Retrieves a document by its id."""
    document=db_session.get(Document,document_id)
    return document

def update_document(*,db_session:Session, document_in:Document,update_info:dict)->Document:
    """Updates document uploaded_at date or filename."""
    document_in.sqlmodel_update(update_info)
    db_session.add(document_in)
    db_session.commit()
    db_session.refresh(document_in)
    return document_in

def delete_document(*,db_session:Session, document_in:Document)->None:
    """Deletes document."""
    db_session.delete(document_in)
    db_session.commit()


def delete_project(*,db_session:Session, project_in:Project)->None:
    """Deletes a project along with its associated documents and members (ProjectMember)."""
    db_session.delete(project_in)
    db_session.commit()


def delete_user(*,db_session:Session, user_in:User)->None:
    """Deletes user"""
    db_session.delete(user_in)
    db_session.commit()













































