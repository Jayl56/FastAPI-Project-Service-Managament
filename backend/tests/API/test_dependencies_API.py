import uuid
from datetime import timedelta
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException, UploadFile
from sqlmodel import Session

import backend.core.dependencies as control
import backend.crud_db as crud
from backend.core.app_config import settings
from backend.core.security import ALGORITHM, create_access_token
from backend.models.models_API import ProjectAccess, UserCreate
from backend.models.models_db import Document, Project, User
from backend.tests.utils.users import create_random_user
from backend.tests.utils.utils import random_email, random_lower_string


def test_get_current_user(
        db:Session,
        test_user_token_headers
)->None:

    token = test_user_token_headers["Authorization"].split(" ")[1]
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

@pytest.mark.parametrize("size",[settings.PROJECT_STORAGE_LIMIT_BYTES+1,settings.PROJECT_STORAGE_LIMIT_BYTES])
def test_validate_project_storage_limit_exceed(
        db:Session,
        crud_test_project:Project,
        size:int)->None:

    mock_file=MagicMock()
    mock_file.file=MagicMock()

    with patch("backend.core.dependencies.get_file_size") as mock_func_size:
        mock_func_size.return_value=size
        with pytest.raises(HTTPException) as exc:
            control.validate_project_storage_limit(
            db_session=db,
            project=crud_test_project,
            files=[mock_file],)

    assert exc.value.status_code==409
    assert exc.value.detail=="Uploading these files would exceed the project's storage limit."
    mock_func_size.assert_called_once()

def test_validate_project_storage_limit_valid_files(
        db:Session,
        crud_test_project:Project,
)->None:

    mock_file = MagicMock()
    mock_file.file = MagicMock()

    with patch("backend.core.dependencies.get_file_size") as mock_func_size:
        mock_func_size.return_value=settings.PROJECT_STORAGE_LIMIT_BYTES-1
        control.validate_project_storage_limit(
        db_session=db,
        project=crud_test_project,
        files=[mock_file])

    mock_func_size.assert_called_once()









