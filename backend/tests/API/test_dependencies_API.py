import backend.core.dependencies as control
from backend.core.app_config import settings
from backend.core.security import create_access_token,ALGORITHM
from backend.models.models_API import UserCreate,ProjectAccess
from backend.models.models_db import User,Project,Document
from backend.tests.utils.utils import random_email, random_lower_string
from backend.tests.utils.users import create_random_user
import backend.crud_db as crud
from sqlmodel import Session
from datetime import timedelta
import pytest
from fastapi import HTTPException
import jwt
import uuid

def test_get_current_user(
        db:Session,
        owner_user_token_headers:dict[str,str]
)->None:

    token = owner_user_token_headers["Authorization"].split(" ")[1]
    user =control.get_current_user(db,token)
    user_db=crud.get_user_by_email(
        db_session=db,
        email=settings.EMAIL_TEST_USER)
    assert user.user_id==user_db.user_id

def test_get_current_user_expired_token_error(db:Session)->None:
    expired_token=create_access_token(
        random_lower_string(),
        timedelta(seconds=-1)
    )
    with pytest.raises(HTTPException) as exc:
       control.get_current_user(db,expired_token)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Token has expired, please log in again"

def test_get_current_user_invalid_token_error(db:Session,crud_test_user:User)->None:
    invalid_token = jwt.encode(
        {"sub": str(crud_test_user.user_id)},
        "wrong-secret-for-token-validation",
        algorithm=ALGORITHM,
    )
    with pytest.raises(HTTPException) as exc:
       control.get_current_user(db,invalid_token)

    assert exc.value.status_code == 403
    assert exc.value.detail == "Could not validate credentials"

def test_get_current_user_validation_error(db:Session)->None:
    invalid_token = jwt.encode(
        {"sub": "invalid-uuid-for-user-validation"},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )
    with pytest.raises(HTTPException) as exc:
        control.get_current_user(db,invalid_token)

    assert exc.value.status_code == 403
    assert exc.value.detail == "Could not validate credentials"

def test_get_current_user_non_existent_user_error(
        db:Session,
        user_create:UserCreate)->None:

    fake_id=uuid.uuid4()
    token=create_access_token(fake_id,timedelta(minutes=1))
    with pytest.raises(HTTPException) as exc:
        control.get_current_user(db,token)
    assert exc.value.status_code == 404
    assert exc.value.detail == "User does not exist"

def test_get_actual_project(db:Session,crud_test_project:Project)->None:
    p_id=crud_test_project.project_id
    project_out=control.get_actual_project(db, p_id)
    assert project_out.project_id == p_id

def test_get_actual_project_non_existent_project_error(db:Session)->None:
    fake_id=uuid.uuid4()
    with pytest.raises(HTTPException) as exc:
        control.get_actual_project(db,fake_id)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Project does not exist."

@pytest.mark.parametrize("role",list(ProjectAccess))
def test_is_member(
        db:Session,
        crud_test_project:Project,
        crud_test_user:User,role):

    user_in = UserCreate(
        username=random_lower_string(),
        email=random_email(),
        password=random_lower_string(),
    )
    if role != ProjectAccess.owner:
       no_owner_member=crud.create_user(db_session=db,user_create=user_in)
       crud.create_project_member(
        db_session=db,
        project_id=crud_test_project.project_id,
        user_id=no_owner_member.user_id,
        member_type=role)
       member_out=control.is_member(db,crud_test_project,no_owner_member)
    else:
       member_out=control.is_member(db,crud_test_project,crud_test_user)
    assert member_out

def test_is_member_not_enough_permissions_to_project(
        db:Session,
        crud_test_project:Project)->None:
    user_in = UserCreate(
        username=random_lower_string(),
        email=random_email(),
        password=random_lower_string(),
    )
    user2=crud.create_user(
        db_session=db,
        user_create=user_in)

    with pytest.raises(HTTPException) as exc:
        control.is_member(db,crud_test_project,user2)

    assert exc.value.status_code == 403
    assert exc.value.detail == "Not enough permissions.You are neither a participant nor an owner of this project."

def test_is_owner(
        db:Session,
        crud_test_project:Project,
        crud_test_user:User)->None:
    member=crud.authenticate_project_member(
        db_session=db,
        project_id=crud_test_project.project_id,
        user_id=crud_test_user.user_id)
    owner=control.is_owner(member)
    assert owner

@pytest.mark.parametrize("role",list(ProjectAccess))
def test_is_owner_common_member_error(
        db:Session,
        crud_test_project:Project,
        role
)->None:
    if role != ProjectAccess.owner:
     user_in = UserCreate(
        username=random_lower_string(),
        email=random_email(),
        password=random_lower_string(),
        )
     user2=crud.create_user(db_session=db, user_create=user_in)
     crud.create_project_member(
        db_session=db,
        project_id=crud_test_project.project_id,
        user_id=user2.user_id,
        member_type=role)
     member = crud.authenticate_project_member(
         db_session=db,
         project_id=crud_test_project.project_id,
        user_id=user2.user_id)
     with pytest.raises(HTTPException) as exc:
        control.is_owner(member)

     assert exc.value.status_code == 403
     assert exc.value.detail == "Not enough permissions, you are not the project's owner."

def test_get_actual_document(
        db:Session,
        doc_for_crud_test_project:Document,
        crud_test_project:Project,
        crud_test_user:User
)->None:
    doc_out=control.get_actual_document(db, doc_for_crud_test_project.doc_id,crud_test_user)
    project_doc=crud_test_project.documents[0]
    assert doc_out
    assert doc_out.filename==project_doc.filename

def test_get_actual_document_non_authorized_user_error(
        db:Session,
        doc_for_crud_test_project:Project,
        crud_test_project:Project
)->None:
    user_non_auth=create_random_user(db)
    with pytest.raises(HTTPException) as exc:
        control.get_actual_document(db, doc_for_crud_test_project.doc_id, user_non_auth)

    assert exc.value.status_code == 403
    assert exc.value.detail == "You are not a member of the project this document belongs to."

def test_get_actual_document_non_existent_doc_error(
        db:Session,
        crud_test_user:User
)->None:
    fake_id=uuid.uuid4()
    with pytest.raises(HTTPException) as exc:
        control.get_actual_document(db,fake_id,crud_test_user)
    assert exc.value.status_code == 404
    assert exc.value.detail == "Document does not exist."









