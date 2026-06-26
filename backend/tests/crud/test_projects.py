from fastapi.encoders import jsonable_encoder
import datetime
import pytest
from backend.models.models_db import Project,Document,User
from backend.models.models_API import (
    UserCreate, CreateProject, ProjectAccess, UpdateProject,
    UploadDocuments
)
from backend.tests.utils.utils import random_email, random_lower_string
from backend.tests.utils.documents import create_random_docs_for_project
from backend.tests.utils.projects import create_random_participant
import backend.crud_db as crud
from sqlmodel import Session


def test_create_project(
        db:Session,
        crud_test_user:User,
        project_create:CreateProject
)->None:
    project=crud.create_project(
        db_session=db,
        new_project=project_create,
        owner_id=crud_test_user.user_id
    )

    assert project.project_id
    assert project.name==project_create.name
    assert project.description==project_create.description
    assert len(project.members)==1
    owner_auth=crud.authenticate_project_member(
        db_session=db,
        project_id=project.project_id,
        user_id=crud_test_user.user_id
    )
    assert owner_auth
    assert owner_auth.role==ProjectAccess.owner


def test_get_project_by_id(
        db:Session,
        crud_test_user:User,
        crud_test_project:Project
)->None:
    project_out=crud.get_project_by_id(
        db_session=db,
        project_id=crud_test_project.project_id
    )
    assert project_out
    assert project_out.name==crud_test_project.name
    assert project_out.description==crud_test_project.description
    assert jsonable_encoder(project_out)==jsonable_encoder(crud_test_project)

def test_update_project_details(
        db:Session,
        crud_test_project:Project
)->None:
    new_project_info=UpdateProject(
        name=random_lower_string(),
        description=random_lower_string(),
    )
    project=crud.update_project_details(
        db_session=db,
        original_project=crud_test_project,
        info_to_update=new_project_info
    )
    assert project.name==new_project_info.name
    assert project.description==new_project_info.description

def test_update_project_no_info_return_original(
        db:Session,
        crud_test_project:Project,
        crud_test_user:User
)->None:
    new_project_info=UpdateProject()
    project = crud.update_project_details(
        db_session=db,
        original_project=crud_test_project,
        info_to_update=new_project_info
    )
    assert project.name == crud_test_project.name
    assert project.description == crud_test_project.description

@pytest.mark.parametrize("role", list(ProjectAccess))
def test_upload_documents_for_project_member(
    db: Session,
    crud_test_user: User,
    docs_to_upload: UploadDocuments,
    crud_test_project: Project,
    role: ProjectAccess,
) -> None:

    member = crud_test_user

    if role != ProjectAccess.owner:
        member = crud.create_user(
            db_session=db,
            user_create=UserCreate(
                username=random_lower_string(),
                email=random_email(),
                password=random_lower_string(),
            ),
        )

        crud.create_project_member(
            db_session=db,
            project_id=crud_test_project.project_id,
            user_id=member.user_id,
            member_type=role,
        )

    crud.upload_documents_for_project(
        db_session=db,
        project_id=crud_test_project.project_id,
        user_id=member.user_id,
        upload_docs=docs_to_upload,
    )

    assert len(crud_test_project.documents) == len(docs_to_upload.documents)

    expected_filenames = {
        doc.filename
        for doc in docs_to_upload.documents
    }

    uploaded_filenames = {
        doc.filename
        for doc in crud_test_project.documents
    }

    assert uploaded_filenames == expected_filenames

    assert all(
        doc.uploaded_by == member.user_id
        for doc in crud_test_project.documents
    )

    assert all(
        isinstance(doc.uploaded_at, datetime.datetime)
        for doc in crud_test_project.documents
    )

def test_upload_no_documents_for_project(
        db:Session,
        crud_test_user:User,
        crud_test_project:Project)->None:
    empty_entry=UploadDocuments()
    crud.upload_documents_for_project(
        db_session=db,
        project_id=crud_test_project.project_id,
        user_id=crud_test_user.user_id,
        upload_docs=empty_entry
    )
    assert crud_test_project.documents ==[]

@pytest.mark.parametrize(
    "role",
    [r for r in ProjectAccess if r != ProjectAccess.owner]
)
def test_get_available_projects_returns_owned_and_member_projects(
        db:Session,
        crud_test_project:Project,
        crud_test_user:User,
        role:ProjectAccess
)->None:
    new_user=UserCreate(
        username=random_lower_string(),
        email=random_email(),
        password=random_lower_string(),
    )
    new_project=CreateProject(
        name=random_lower_string(),
        description=random_lower_string(),
    )
    user2=crud.create_user(
        db_session=db,
        user_create=new_user
    )
    project2=crud.create_project(
        db_session=db,
        new_project=new_project,
        owner_id=user2.user_id
    )
    crud.create_project_member(
        db_session=db,
        project_id=project2.project_id,
        user_id=crud_test_user.user_id,
        member_type=role
    )

    expected_ids={crud_test_project.project_id,project2.project_id}

    total_projects=crud.get_available_projects_user_role(
        db_session=db,
        user_id=crud_test_user.user_id
    )

    returned_ids={project.project_id for project in total_projects}

    assert len(total_projects)==2
    assert returned_ids==expected_ids

def test_get_available_projects_owner_filter(
        db:Session,
        crud_test_project:Project,
        crud_test_user:User
)->None:
    total_projects=crud.get_available_projects_user_role(
        db_session=db,
        user_id=crud_test_user.user_id,
        role=ProjectAccess.owner
    )
    assert len(total_projects)==1
    assert total_projects[0].project_id==crud_test_project.project_id


@pytest.mark.parametrize(
    "role",
    [r for r in ProjectAccess if r != ProjectAccess.owner]
)
def test_get_available_projects_role_filter(
        db: Session,
        crud_test_project: Project,
        crud_test_user: User,
        role: ProjectAccess
) -> None:
    new_user = UserCreate(
        username=random_lower_string(),
        email=random_email(),
        password=random_lower_string(),
    )
    new_project = CreateProject(
        name=random_lower_string(),
        description=random_lower_string(),
    )
    user2 = crud.create_user(
        db_session=db,
        user_create=new_user
    )
    project2 = crud.create_project(
        db_session=db,
        new_project=new_project,
        owner_id=user2.user_id
    )
    crud.create_project_member(
        db_session=db,
        project_id=project2.project_id,
        user_id=crud_test_user.user_id,
        member_type=role
    )

    total_projects = crud.get_available_projects_user_role(
        db_session=db,
        user_id=crud_test_user.user_id,
        role=role
    )

    returned_ids = {
        project.project_id
        for project in total_projects
    }

    assert returned_ids == {project2.project_id}

def test_get_available_projects_for_no_member_user(
        db:Session,
        crud_test_user:User
)->None:
    projects = crud.get_available_projects_user_role(
        db_session=db,
        user_id=crud_test_user.user_id
    )
    assert projects==[]

def test_delete_project_on_cascade_members_and_documents(
        db:Session,
        crud_test_project:Project,
        crud_test_user:User,
        doc_for_crud_test_project:Document
)->None:

    user_participant = create_random_participant(db,crud_test_project)
    project_id=crud_test_project.project_id
    doc_id=doc_for_crud_test_project.doc_id


    crud.delete_project(
        db_session=db,
        project_in=crud_test_project
    )

    project=crud.get_project_by_id(
        db_session=db,
        project_id=project_id
    )
    document=crud.get_document_by_id(
        db_session=db,
        document_id=doc_id
    )
    owner=crud.authenticate_project_member(
        db_session=db,
        project_id=project_id,
        user_id=crud_test_user.user_id
    )
    participant=crud.authenticate_project_member(
        db_session=db,
        project_id=project_id,
        user_id=user_participant.user_id
    )

    assert project is None
    assert document is None
    assert owner is None
    assert participant is None



















