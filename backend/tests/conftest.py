from collections.abc import Generator
import pytest
from io import BytesIO
from fastapi import UploadFile
from fastapi.testclient import TestClient
from sqlmodel import Session
from sqlalchemy import delete

from backend.core.app_config import settings
from backend.models.models_API import UserCreate,CreateProject,UploadDocuments
from backend.models.models_db import User,Project,ProjectMember,Document
from backend.core.dependencies import engine,init_db
from backend.main import app
import backend.crud_db as crud
from backend.tests.utils.users import authentication_token_from_email,authentication_data_from_email
from backend.tests.utils.documents import create_random_docs,create_random_docs_for_project
from backend.tests.utils.utils import random_email, random_lower_string


@pytest.fixture(autouse=True)
def db()->Generator[Session,None,None]:
    with Session(engine) as session:
      init_db()
      yield session
      models=[ProjectMember,Document,Project,User]
      for model in models:
          session.exec(delete(model))
      session.commit()

@pytest.fixture
def user_create()->UserCreate:
    user_in = UserCreate(
        username=random_lower_string(),
        email=random_email(),
        password=random_lower_string(),
    )
    return user_in

@pytest.fixture
def project_create()->CreateProject:
    project_in = CreateProject(
        name=random_lower_string(),
        description=random_lower_string()
    )
    return project_in

@pytest.fixture
def docs_to_upload()->UploadDocuments:
    docs=create_random_docs(5)
    return docs

@pytest.fixture
def files_to_upload() -> list[tuple]:
    return [
        (
            "files",
            (
                "document1.pdf",
                BytesIO(b"%PDF-1.4 fake pdf content"),
                "application/pdf",
            ),
        ),
        (
            "files",
            (
                "document2.docx",
                BytesIO(b"PK\x03\x04 fake docx content"),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
        ),
        (
            "files",
            (
                "document3.doc",
                BytesIO(b"\xd0\xcf\x11\xe0 fake doc content"),
                "application/msword",
            ),
        ),
    ]

@pytest.fixture
def crud_test_user(
        db:Session,
        user_create:UserCreate
)->User:
    user = crud.create_user(
        db_session=db,
        user_create=user_create
    )
    return user

@pytest.fixture
def crud_test_project(
        db:Session,
        crud_test_user:User,
        project_create:CreateProject
)->Project:
    project=crud.create_project(
        db_session=db,
        new_project=project_create,
        owner_id=crud_test_user.user_id
    )
    return project

@pytest.fixture
def doc_for_crud_test_project(
        db:Session,
        crud_test_project:Project
)->Document:
    doc=create_random_docs_for_project(db,crud_test_project)[0]
    return doc

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def test_user_token_headers(
        client:TestClient,
        db:Session
)->dict[str, str]:
    return authentication_token_from_email(
        client=client,
        email=settings.EMAIL_TEST_USER,
        db=db
    )

@pytest.fixture
def test_user_auth_data(
    client: TestClient,
    db: Session,
) -> dict[str, str]:
    return authentication_data_from_email(
        client=client,
        email=settings.EMAIL_TEST_USER,
        db=db,
    )

@pytest.fixture
def test_user_project(
        db:Session,
        project_create:CreateProject
)->Project:
    test_user=crud.get_user_by_email(
        db_session=db,
        email=settings.EMAIL_TEST_USER
    )
    project=crud.create_project(
        db_session=db,
        new_project=project_create,
        owner_id=test_user.user_id
    )
    return project

@pytest.fixture
def doc_for_test_user_project(
    db: Session,
    test_user_project: Project,
) -> Document:
    doc = create_random_docs_for_project(
        db,
        test_user_project,
        None,
    )[0]
    return doc



