from io import BytesIO
from sqlmodel import Session
from fastapi.testclient import TestClient
import backend.crud_db as crud
from backend.core.app_config import settings
from backend.models.models_db import Document
from backend.models.models_API import DocumentPublic,DocumentDownloadResponse
from unittest.mock import patch



def test_download_document(
    client: TestClient,
        test_user_token_headers,
    doc_for_test_user_project: Document,
):
    expected_url = (
        "https://fake-bucket.s3.amazonaws.com/file.pdf"
    )
    with patch(
            "backend.API.documents.s3_utils.get_s3_doc_url_download",
            return_value=expected_url,
    ) as mock_download:
      r = client.get(
        f"{settings.API_HOST}/document/{doc_for_test_user_project.doc_id}",
        headers=test_user_token_headers,
         )

    mock_download.assert_called_once_with(
        settings.S3_BUCKET_NAME,
        doc_for_test_user_project.s3_key,
    )
    document=DocumentDownloadResponse.model_validate(r.json())

    assert r.status_code == 200
    assert document.url_to_download


def test_update_document(
    db: Session,
    client: TestClient,
        test_user_token_headers,
    doc_for_test_user_project: Document,
):
    with patch (
        "backend.API.documents.s3_utils.update_s3_file_object",
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
            headers=test_user_token_headers,
        )
    content = r.json()
    document = DocumentPublic.model_validate(content)
    db.refresh(doc_for_test_user_project)
    expected_s3_key = doc_for_test_user_project.s3_key
    args, kwargs = mock_update.call_args

    assert r.status_code == 200
    mock_update.assert_called_once()
    assert args[0] == "s3buckettest5160"

    uploaded_file = args[1]

    assert uploaded_file.filename == "nuevo.pdf"
    assert uploaded_file.content_type == "application/pdf"
    assert args[2] == expected_s3_key
    assert document.filename == "nuevo.pdf"
    assert document.file_size== doc_for_test_user_project.file_size


def test_delete_document(
    db: Session,
    client: TestClient,
        test_user_token_headers,
    doc_for_test_user_project: Document,
):
    doc_id = doc_for_test_user_project.doc_id
    s3_key=doc_for_test_user_project.s3_key
    with patch(
            "backend.API.documents.s3_utils.delete_s3_file_object"
    ) as mock_delete:
      r = client.delete(
        f"{settings.API_HOST}/document/{doc_id}",
        headers=test_user_token_headers,
       )

    db.expire_all()
    deleted_doc = crud.get_document_by_id(
        db_session=db,
        document_id=doc_id,
    )
    assert r.status_code == 204
    mock_delete.assert_called_once_with(
        settings.S3_BUCKET_NAME,
        s3_key,
    )
    assert deleted_doc is None


