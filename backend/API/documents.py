from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, File, UploadFile, status

import backend.crud_db as crud_db
import backend.utils.s3_utils as s3_utils
from backend.core.app_config import settings
from backend.core.dependencies import (AvailableDoc, SessionDep,
                                       validate_project_storage_limit)
from backend.models.models_API import DocumentDownloadResponse, DocumentPublic

router=APIRouter(prefix="/document",tags=["documents"])

@router.get("/{doc_id}",
            status_code=status.HTTP_200_OK)
def download_document(*,document:AvailableDoc)->DocumentDownloadResponse:
    url=s3_utils.get_s3_doc_url_download(
        settings.S3_BUCKET_NAME,
        document.s3_key
    )
    return DocumentDownloadResponse(url_to_download=url)

@router.put("/{doc_id}",
            response_model=DocumentPublic,
            status_code=status.HTTP_200_OK)
def update_document(
        *,session:SessionDep,
        document:AvailableDoc,
        file:Annotated[UploadFile, File(...)]
)->DocumentPublic:

    validate_project_storage_limit(
        db_session=session,
        project=crud_db.get_project_by_id(
            db_session=session,
            project_id=document.project_id
        ),
        files=[file]
    )

    update_data = {
        "filename": file.filename,
        "uploaded_at": datetime.now(timezone.utc)
    }

    s3_utils.update_s3_file_object(
        settings.S3_BUCKET_NAME,
        file,
        document.s3_key
    )

    doc_updated=crud_db.update_document(
        db_session=session,
        document_in=document,
        update_info=update_data
    )

    return doc_updated

@router.delete("/{doc_id}",
               status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
        *,session:SessionDep,
        document:AvailableDoc
)->None:
    s3_utils.delete_s3_file_object(
        settings.S3_BUCKET_NAME,
        document.s3_key
    )
    crud_db.delete_document(
        db_session=session,
        document_in=document
    )









