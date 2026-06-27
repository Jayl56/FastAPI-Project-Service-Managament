from sqlmodel import Session
from fastapi import UploadFile
from fastapi.testclient import TestClient
from backend.core.app_config import settings
from backend.models.models_db import Project,User
from backend.models.models_API import (
    UserCreate,
    ProjectAccess,
    ProjectPublicInfo,
    ProjectPublic,
    ProjectsPublic,
    DocumentsPublic)
from backend.utils.email_utils import EmailData,generate_email_token
from backend.tests.utils.documents import create_random_docs_for_project
from backend.tests.utils.utils import random_lower_string,random_email
import backend.crud_db as crud
from unittest.mock import patch
import datetime
import uuid
import pytest




def test_generate_project(
        db: Session,
        test_user_token_headers,
        client: TestClient
):
    data={"name":"New Project",
          "description":"This is a new project"}

    r=client.post(
        f"{settings.API_HOST}/projects",
        headers=test_user_token_headers,
        json=data
    )

    created_project=ProjectPublicInfo.model_validate(r.json())

    assert r.status_code==201
    assert created_project.name==data["name"]
    assert created_project.description==data["description"]
    assert created_project.project_id
    assert isinstance(created_project.updated_at,datetime.datetime)


@pytest.mark.parametrize(
    "role",
    [r for r in ProjectAccess if r != ProjectAccess.owner]
)
def test_get_projects_all_for_user(
    db:Session,
    client: TestClient,
        test_user_token_headers,
    test_user_project:Project,
    crud_test_project:Project,
    role:ProjectAccess,
):
    test_user = crud.get_user_by_email(
        db_session=db,
        email=settings.EMAIL_TEST_USER,
    )

    crud.create_project_member(
        db_session=db,
        project_id=crud_test_project.project_id,
        user_id=test_user.user_id,
        member_type=role,
    )

    response = client.get(
        f"{settings.API_HOST}/projects",
        headers=test_user_token_headers,
    )

    projects_info=ProjectsPublic.model_validate(response.json())
    expected_ids = {
        test_user_project.project_id,
        crud_test_project.project_id,
    }
    returned_ids = {
        project.project_id
        for project in projects_info.projects
    }

    assert response.status_code == 200
    assert projects_info.count_projects == len(expected_ids)
    assert returned_ids == expected_ids

def test_get_projects_for_owner(
    db:Session,
    client: TestClient,
        test_user_token_headers,
    test_user_project: Project,
):
    r=client.get(
        f"{settings.API_HOST}/projects/?role={ProjectAccess.owner.value}",
            headers=test_user_token_headers
    )
    project_info=ProjectsPublic.model_validate(r.json())

    assert r.status_code == 200
    assert project_info.count_projects == 1
    assert project_info.projects[0].project_id == test_user_project.project_id

@pytest.mark.parametrize(
    "role",
    [r for r in ProjectAccess if r != ProjectAccess.owner]
)
def test_get_projects_for_role(
    db:Session,
    client: TestClient,
        test_user_token_headers,
    crud_test_project: Project,
    role:ProjectAccess,
):
    test_user = crud.get_user_by_email(
        db_session=db,
        email=settings.EMAIL_TEST_USER)
    crud.create_project_member(
        db_session=db,
        project_id=crud_test_project.project_id,
        user_id=test_user.user_id,
        member_type=role)
    response =client.get(
        f"{settings.API_HOST}/projects/?role={role.value}",
        headers=test_user_token_headers
    )
    project_info = ProjectsPublic.model_validate(response.json())

    assert response.status_code == 200
    assert project_info.count_projects == 1
    assert project_info.projects[0].project_id == crud_test_project.project_id

def test_get_projects_with_document(
    db:Session,
    client: TestClient,
        test_user_token_headers,
    test_user_project: Project,
):
    doc=create_random_docs_for_project(db,test_user_project)[0]
    r=client.get(
        f"{settings.API_HOST}/projects/",
        headers=test_user_token_headers
    )
    project_info = ProjectsPublic.model_validate(r.json())
    doc_from_r=project_info.projects[0].documents[0]

    assert r.status_code == 200
    assert project_info.count_projects == 1
    assert doc_from_r.filename==doc.filename
    assert isinstance(doc_from_r.uploaded_at,datetime.datetime)

def test_get_project_info(
    db:Session,
    client: TestClient,
        test_user_token_headers,
    test_user_project: Project,):

    r = client.get(
        f"{settings.API_HOST}/project/{test_user_project.project_id}/info",
        headers=test_user_token_headers
    )

    project = ProjectPublicInfo.model_validate(r.json())
    assert r.status_code == 200
    assert project.name == test_user_project.name
    assert project.description ==test_user_project.description
    assert project.project_id
    assert isinstance(project.updated_at, datetime.datetime)

def test_update_project_info_by_owner(
        db:Session,
        client:TestClient,
        test_user_token_headers,
        test_user_project: Project):

    new_info={"name":random_lower_string(),
        "description":random_lower_string()
    }

    r =client.put(
        f"{settings.API_HOST}/project/{test_user_project.project_id}/info",
        headers=test_user_token_headers,
        json=new_info
    )
    project=ProjectPublicInfo.model_validate(r.json())
    db.refresh(test_user_project)

    assert r.status_code == 200
    assert  project.name == new_info["name"]
    assert project.description == new_info["description"]
    assert project.updated_at == test_user_project.updated_at



def test_update_project_info_with_no_info(
        db:Session,client: TestClient,
        test_user_token_headers,
        test_user_project: Project):

    new_info = {}

    r = client.put(
        f"{settings.API_HOST}/project/{test_user_project.project_id}/info",
            headers=test_user_token_headers,
            json=new_info
    )

    project = ProjectPublicInfo.model_validate(r.json())
    db.refresh(test_user_project)

    assert r.status_code == 200
    assert project.name == test_user_project.name
    assert project.description == test_user_project.description
    assert project.updated_at == test_user_project.updated_at


def test_upload_new_docs_for_project(
    client: TestClient,
        test_user_token_headers,
    test_user_project: Project,
    files_to_upload:list[UploadFile]):

    with patch(
            "backend.API.projects.s3_utils.upload_s3_file_object",
            side_effect=lambda *args, **kwargs: random_lower_string()
    ) as mock_upload:
       r =client.post(
           f"{settings.API_HOST}/project/{test_user_project.project_id}/documents",
           headers=test_user_token_headers,
           files=files_to_upload
       )

    project=ProjectPublic.model_validate(r.json())
    docs_from_r=project.documents

    expected_filenames = {
        file[1][0]
        for file in files_to_upload
    }

    returned_filenames={
        doc.filename for doc in docs_from_r
    }

    assert r.status_code == 201
    assert mock_upload.call_count==len(files_to_upload)
    assert len(docs_from_r)==len(files_to_upload)
    assert expected_filenames==returned_filenames

def test_get_project_docs(
        db:Session,
        client: TestClient,
        test_user_token_headers,
        test_user_project: Project,
        ):

        docs=create_random_docs_for_project(db,test_user_project,None,5)
        expected_filenames={
            doc.filename for doc in docs
        }

        r =client.get(
            f"{settings.API_HOST}/project/{test_user_project.project_id}/documents",
            headers=test_user_token_headers
        )

        returned_docs=DocumentsPublic.model_validate(r.json()).documents

        returned_filenames={
            doc.filename for doc in returned_docs
        }

        assert r.status_code == 200
        assert len(returned_docs)==5
        assert expected_filenames==returned_filenames

def test_delete_project_as_project_participant_error(
    db: Session,
    client: TestClient,
        test_user_token_headers,
    crud_test_project: Project,
) -> None:

    test_user=crud.get_user_by_email(
        db_session=db,
        email=settings.EMAIL_TEST_USER)
    crud.create_project_member(
        db_session=db,
        project_id=crud_test_project.project_id,
        user_id=test_user.user_id,
        member_type=ProjectAccess.participant,
    )

    r = client.delete(
        f"{settings.API_HOST}/project/{crud_test_project.project_id}",
        headers=test_user_token_headers,
    )

    assert r.status_code == 403

def test_delete_project_as_owner_success(
    db:Session,
    client: TestClient,
        test_user_token_headers,
    test_user_project: Project,
) -> None:

    test_project_id=test_user_project.project_id
    r = client.delete(
        f"{settings.API_HOST}/project/{test_user_project.project_id}",
        headers=test_user_token_headers,
    )
    db.expire_all()
    deleted_project=crud.get_project_by_id(
        db_session=db,
        project_id=test_project_id,)

    assert deleted_project is None
    assert r.status_code == 204

def test_invite_user_as_participant(
    client: TestClient,
    crud_test_user: User,
        test_user_token_headers,
    test_user_project: Project,
     ):

    r= client.post(
        f"{settings.API_HOST}/project/{test_user_project.project_id}/invite",
            headers=test_user_token_headers,
            params={"email": crud_test_user.email}
    )

    assert r.status_code == 201
    assert r.json()["message"]==f"User {crud_test_user.username} was successfully invited to the project: {test_user_project.name}."

def test_invite_non_existent_user_error(
    client: TestClient,
        test_user_token_headers,
    test_user_project: Project,

):
    email=random_email()
    r= client.post(
        f"{settings.API_HOST}/project/{test_user_project.project_id}/invite",
            headers=test_user_token_headers,
            params={"email": email}
    )
    assert r.status_code == 404
    assert r.json()["detail"]=="User with provided email does not exist."

def test_invite_same_owner_error(
    client: TestClient,
        test_user_token_headers,
    test_user_project: Project,

):
    email=settings.EMAIL_TEST_USER
    r = client.post(
        f"{settings.API_HOST}/project/{test_user_project.project_id}/invite",
            headers=test_user_token_headers,
            params={"email": email}
    )
    assert r.status_code == 400
    assert r.json()["detail"]=="You can't invite yourself to a project."

def test_invite_user_already_member_error(
    client: TestClient,
        test_user_token_headers,
    test_user_project: Project,
    crud_test_user: User,
    db:Session):

    crud.create_project_member(
        db_session=db,
        project_id=test_user_project.project_id,
        user_id=crud_test_user.user_id,
        member_type=ProjectAccess.participant,
    )

    r = client.post(
        f"{settings.API_HOST}/project/{test_user_project.project_id}/invite",
            headers=test_user_token_headers,
            params={"email":crud_test_user.email}
    )

    assert r.status_code == 409
    assert r.json()["detail"]==f"User with provided email is already member of this project: {test_user_project.name}."


def test_share_project_user_not_found(
    client: TestClient,
        test_user_token_headers,
    test_user_project: Project,
):
    r = client.post(
        f"{settings.API_HOST}/project/{test_user_project.project_id}/share",
        params={"email": "ghost@test.com"},
        headers=test_user_token_headers,
    )

    assert r.status_code == 404
    assert r.json()["detail"] == (
        "User with provided email to share does not exist."
    )


def test_share_project_to_self(
    client: TestClient,
        test_user_token_headers,
    test_user_project:Project
):
    r = client.post(
        f"{settings.API_HOST}/project/{test_user_project.project_id}/share",
        params={"email": settings.EMAIL_TEST_USER},
        headers=test_user_token_headers,
    )
    assert r.status_code == 400
    assert r.json()["detail"] == (
        "You can't share a project with yourself."
    )


def test_share_project_existing_member(
    db: Session,
    client: TestClient,
        test_user_token_headers,
    crud_test_user: User,
    test_user_project: Project,
):
    crud.create_project_member(
        db_session=db,
        project_id=test_user_project.project_id,
        user_id=crud_test_user.user_id,
        member_type=ProjectAccess.participant,
    )
    r = client.post(
        f"{settings.API_HOST}/project/{test_user_project.project_id}/share",
        params={"email": crud_test_user.email},
        headers=test_user_token_headers,
    )

    assert r.status_code == 409
    assert (
        r.json()["detail"]
        == (
            f"User with provided email is already member "
            f"of this project: {test_user_project.name}."
        )
    )


@patch("backend.API.projects.send_email")
@patch("backend.API.projects.generate_invitation_email")
@patch("backend.API.projects.generate_email_token")
def test_share_project_success(
    mock_generate_token,
    mock_generate_email,
    mock_send_email,
    client: TestClient,
        test_user_token_headers,
    crud_test_user: User,
    test_user_project: Project,
):
    mock_generate_token.return_value = "fake-token"

    mock_generate_email.return_value = EmailData(
        subject="Invitation",
        html_content="<p>Invitation</p>",
    )

    r = client.post(
        f"{settings.API_HOST}/project/{test_user_project.project_id}/share",
        params={"email": crud_test_user.email},
        headers=test_user_token_headers,
    )

    assert r.status_code == 201

    assert r.json() == {
        "message": (
            f"Invitation has been sent to "
            f"{crud_test_user.email}."
        )
    }

    mock_generate_token.assert_called_once()

    mock_generate_email.assert_called_once()

    mock_send_email.assert_called_once_with(
        email_receptor=crud_test_user.email,
        subject="Invitation",
        html_content="<p>Invitation</p>",
    )

def test_validate_invitation_project_success(
    db: Session,
    client: TestClient,
        test_user_auth_data,
    crud_test_project: Project,
):
    test_user=crud.get_user_by_email(
        db_session=db,
        email=settings.EMAIL_TEST_USER)
    payload = {
        "user_invited_id": str(test_user.user_id),
        "project_id": str(crud_test_project.project_id),
    }
    token=generate_email_token(payload,settings.EMAIL_INVITATION_TOKEN_EXPIRE_HOURS)

    data={"token": token,
          "email": test_user.email,
          "password": test_user_auth_data["password"],
          }

    r = client.post(f"{settings.API_HOST}/join-project",data=data)

    assert r.status_code == 201
    assert r.json()["message"] == f"Welcome {test_user.username}! You have successfully joined to this project as a participant."

def test_validate_invitation_project_invalid_token_error(
    db: Session,
    client: TestClient,
    ):
    data={"token":"invalid-token",
          "email":random_email(),
          "password":random_lower_string(),}
    r = client.post(f"{settings.API_HOST}/join-project",data=data)

    assert r.status_code == 401
    assert r.json()["detail"] == "Invitation token is invalid."

def test_validate_invitation_project_non_existent_user_invited_error(
    db: Session,
    client: TestClient,
    crud_test_project: Project,
):
    fake_id=uuid.uuid4()
    payload = {
        "user_invited_id": str(fake_id),
        "project_id": str(crud_test_project.project_id),
    }
    token = generate_email_token(
        payload,
        settings.EMAIL_INVITATION_TOKEN_EXPIRE_HOURS
    )
    data = {"token": token,
            "email":random_email() ,
            "password": random_lower_string(), }
    r=client.post(f"{settings.API_HOST}/join-project",data=data)
    assert r.status_code == 401
    assert r.json()["detail"] == "Invitation token is invalid."

def test_validate_invitation_project_non_existent_project_error(
        db: Session,
        client: TestClient,
        test_user_auth_data,
        crud_test_project: Project,
):

    fake_id = uuid.uuid4()
    test_user=crud.get_user_by_email(
        db_session=db,
        email=settings.EMAIL_TEST_USER)
    payload = {
        "user_invited_id": str(test_user.user_id),
        "project_id": str(fake_id),
    }
    token = generate_email_token(
        payload,
        settings.EMAIL_INVITATION_TOKEN_EXPIRE_HOURS
    )
    data = {"token": token,
            "email": test_user.email,
            "password": test_user_auth_data["password"], }
    r=client.post(f"{settings.API_HOST}/join-project",data=data)

    assert r.status_code == 404
    assert r.json()["detail"] == "Project does not exist."

def test_validate_invitation_project_current_user_login_error(
        db: Session,
        client: TestClient,
        test_user_auth_data,
        crud_test_project: Project
):

    fake_password=random_lower_string()
    fake_email=random_email()

    test_user=crud.get_user_by_email(
        db_session=db,
        email=settings.EMAIL_TEST_USER)
    payload = {
        "user_invited_id": str(test_user.user_id),
        "project_id": str(crud_test_project.project_id),
    }

    token=generate_email_token(
        payload,
        settings.EMAIL_INVITATION_TOKEN_EXPIRE_HOURS
    )
    data = {"token": token,
            "email": fake_email,
            "password": fake_password}

    r=client.post(f"{settings.API_HOST}/join-project",data=data)

    assert r.status_code == 401
    assert r.json()["detail"] == "Incorrect email or password."

def test_validate_invitation_project_different_auth_user_from_invited_error(
    db: Session,
    client: TestClient,
        test_user_auth_data,
    user_create: UserCreate,
    crud_test_user: User,
    crud_test_project: Project,
):
    test_user = crud.get_user_by_email(
        db_session=db,
        email=settings.EMAIL_TEST_USER)
    payload = {
        "user_invited_id": str(test_user.user_id),
        "project_id": str(crud_test_project.project_id),
    }
    token=generate_email_token(
        payload,
        settings.EMAIL_INVITATION_TOKEN_EXPIRE_HOURS
    )
    data = {"token": token,
            "email": crud_test_user.email,
            "password": user_create.password}
    r=client.post(f"{settings.API_HOST}/join-project",data=data)
    assert r.status_code == 403
    assert r.json()["detail"] == "This invitation is being validated by a different user."

def test_validate_invitation_project_already_member_error(
        db: Session,
        client: TestClient,
        test_user_auth_data,
        crud_test_project: Project,
):
    test_user = crud.get_user_by_email(
        db_session=db,
        email=settings.EMAIL_TEST_USER)

    payload = {
        "user_invited_id": str(test_user.user_id),
        "project_id": str(crud_test_project.project_id),
    }
    token = generate_email_token(
        payload,
        settings.EMAIL_INVITATION_TOKEN_EXPIRE_HOURS
    )

    data = {"token": token,
            "email": test_user.email,
            "password": test_user_auth_data["password"],
            }
    crud.create_project_member(
        db_session=db,
        project_id=crud_test_project.project_id,
        user_id=test_user.user_id,
        member_type=ProjectAccess.participant
        )
    r=client.post(f"{settings.API_HOST}/join-project",data=data)
    assert r.status_code == 409
    assert r.json()["detail"] == "The user is already a participant of the project."






















