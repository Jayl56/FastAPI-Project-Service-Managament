from sqlmodel import Session

import backend.crud_db as crud
from backend.models.models_API import CreateProject, ProjectAccess
from backend.models.models_db import Project, User
from backend.tests.utils.users import create_random_user
from backend.tests.utils.utils import random_lower_string


def create_random_project(db:Session)->Project:
    user=create_random_user(db)
    owner_id=user.user_id
    assert owner_id is not None
    name=random_lower_string()
    description=random_lower_string()
    project_in=CreateProject(name=name,description=description)
    return crud.create_project(db_session=db,new_project=project_in,owner_id=owner_id)

def create_random_participant(db:Session,project_in:Project)->User:
    user=create_random_user(db)
    crud.create_project_member(db_session=db,
                               project_id=project_in.project_id,
                               user_id=user.user_id,
                               member_type=ProjectAccess.participant)
    return user


