from io import BytesIO
from sqlmodel import Session
from fastapi.testclient import TestClient
import backend.crud_db as crud
from backend.core.app_config import settings
from backend.models.models_db import Document,Project
from backend.models.models_API import DocumentPublic,DocumentDownloadResponse
from backend.tests.utils.utils import random_lower_string
from unittest.mock import patch



def test_download_document(
    client: TestClient,
    owner_user_token_headers: dict[str, str],
    doc_for_test_user_project: Document,
):
    expected_url = (
        "https://fake-bucket.s3.amazonaws.com/file.pdf"
    )
    with patch(
            "backend.utils.s3_utils.get_s3_doc_url_download",
            return_value=expected_url,
    ):
      r = client.get(
        f"{settings.API_HOST}/document/{doc_for_test_user_project.doc_id}",
        headers=owner_user_token_headers,
         )

    document=DocumentDownloadResponse.model_validate(r.json())

    assert r.status_code == 200
    assert document.url_to_download


def test_update_document(
    db: Session,
    client: TestClient,
    owner_user_token_headers: dict[str, str],
    doc_for_test_user_project: Document,
):
    with patch (
        "backend.utils.s3_utils.update_s3_file_object",
    ) as mock_update:

       r = client.put(
        f"{settings.API_HOST}/document/{doc_for_test_user_project.doc_id}",
           files={
               "file": (
                   "nuevo.pdf",
                   BytesIO(b"%PDF-1.4 test"),
                   "application/pdf"
               )
           },
            headers=owner_user_token_headers,
        )
    content = r.json()
    document = DocumentPublic.model_validate(content)
    db.refresh(doc_for_test_user_project)

    assert r.status_code == 200
    mock_update.assert_called_once()
    assert document.filename == "nuevo.pdf"
    assert (
        doc_for_test_user_project.filename
        == "nuevo.pdf"
    )


def test_delete_document(
    db: Session,
    client: TestClient,
    owner_user_token_headers: dict[str, str],
    doc_for_test_user_project: Document,
):
    doc_id = doc_for_test_user_project.doc_id

    with patch(
            "backend.utils.s3_utils.delete_s3_file_object"
    ) as mock_delete:
      r = client.delete(
        f"{settings.API_HOST}/document/{doc_id}",
        headers=owner_user_token_headers,
       )

    db.expire_all()
    deleted_doc = crud.get_document_by_id(
        db_session=db,
        document_id=doc_id,
    )
    assert r.status_code == 204
    mock_delete.assert_called_once()
    assert deleted_doc is None


