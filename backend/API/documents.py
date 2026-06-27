from datetime import datetime,timezone
from typing import Annotated
from fastapi import APIRouter,status,File,UploadFile
import backend.crud_db as crud_db
from backend.core.dependencies import SessionDep,AvailableDoc
from backend.models.models_API import (
DocumentDownloadResponse,
DocumentPublic,
)
from backend.core.app_config import settings
import backend.utils.s3_utils as s3_utils



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









