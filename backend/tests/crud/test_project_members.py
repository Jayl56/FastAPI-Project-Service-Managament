import backend.crud_db as crud
import uuid
from backend.models.models_db import ProjectMember,User,Project
from backend.models.models_API import CreateProject,UserCreate,ProjectAccess
from backend.tests.utils.utils import random_email, random_lower_string
from sqlmodel import Session


def test_create_project_member_owner(
        db:Session,
        user_create:UserCreate,
        project_create:CreateProject
):
    user=crud.create_user(
        db_session=db,
        user_create=user_create
    )
    project=crud.create_project(
        db_session=db,
        new_project=project_create,
        owner_id=user.user_id
    )
    owner=crud.authenticate_project_member(
        db_session=db,
        project_id=project.project_id,
        user_id=user.user_id
    )
    assert owner
    assert owner.role==ProjectAccess.owner


def test_get_project_owner(
        db:Session,
        crud_test_project:Project,
        crud_test_user:User
)->None:
    owner=crud.get_project_owner(
        db_session=db,
        project_id=crud_test_project.project_id
    )
    assert owner.user_id == crud_test_user.user_id

def test_create_project_member_participant(
        db:Session,
        crud_test_project:Project
):
    user_in = UserCreate(
        username=random_lower_string(),
        email=random_email(),
        password=random_lower_string(),
    )
    user2=crud.create_user(
        db_session=db,
        user_create=user_in
    )
    crud.create_project_member(
        db_session=db,
        project_id=crud_test_project.project_id,
        user_id=user2.user_id,
        member_type=ProjectAccess.participant
    )
    user_2_auth=crud.authenticate_project_member(
        db_session=db,
        project_id=crud_test_project.project_id,
        user_id=user2.user_id
    )
    assert user_2_auth
    assert user_2_auth.role==ProjectAccess.participant

def test_authenticate_valid_member(
        db:Session,
        crud_test_project:Project,
        crud_test_user:User
):
    member=crud.authenticate_project_member(
        db_session=db,
        project_id=crud_test_project.project_id,
        user_id=crud_test_user.user_id
    )
    assert member

def test_not_authenticate_non_existent_member(
        db:Session,
        crud_test_project:Project
):
    fake_id=uuid.uuid4()
    member = crud.authenticate_project_member(
        db_session=db,
        project_id=crud_test_project.project_id,
        user_id=fake_id
    )
    assert member is None










