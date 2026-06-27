from sqlmodel import Session
from datetime import datetime,timezone
import backend.crud_db as crud
from backend.models.models_db import Project,Document,User
from backend.tests.utils.utils import random_lower_string
from fastapi.encoders import jsonable_encoder


def test_get_document_by_id(
        db:Session,
        crud_test_project:Project,
        crud_test_user:User,
        doc_for_crud_test_project:Document
) -> None:
    doc_out=crud.get_document_by_id(
        db_session=db,
        document_id=doc_for_crud_test_project.doc_id
    )
    assert doc_out
    assert doc_out.filename==doc_for_crud_test_project.filename
    assert jsonable_encoder(doc_out)==jsonable_encoder(doc_for_crud_test_project)

def test_update_document(
        db:Session,
        crud_test_project:Project,
        crud_test_user:User,
        doc_for_crud_test_project:Document
) -> None:
    new_info={"filename":random_lower_string(),
              "uploaded_at":datetime.now(timezone.utc)}
    updated_doc=crud.update_document(
        db_session=db,
        document_in=doc_for_crud_test_project,
        update_info=new_info
    )
    assert updated_doc.filename==new_info["filename"]
    assert updated_doc.uploaded_at==new_info["uploaded_at"]

def test_get_project_storage(
        db:Session,
        crud_test_project:Project,
        doc_for_crud_test_project:Document
)->None:

    doc_size=doc_for_crud_test_project.file_size
    project_size=crud.get_project_storage_used(
        db_session=db,
         project_id=crud_test_project.project_id
    )
    assert project_size==doc_size

def test_get_project_storage_empty_project_return_zero_value(
        db:Session,
        crud_test_project:Project,
):
    project_size=crud.get_project_storage_used(
        db_session=db,
        project_id=crud_test_project.project_id
    )
    assert project_size==0



