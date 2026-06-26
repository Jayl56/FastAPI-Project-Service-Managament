import uuid
from fastapi import UploadFile,HTTPException
from backend.core.aws import s3_client as s3
from pathlib import Path



ALLOWED_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx"
}

async def validate_document(file: UploadFile) -> None:
    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, DOC and DOCX files are allowed."
        )

    header = await file.read(8)
    await file.seek(0)

    if extension == ".pdf":
        if not header.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=400,
                detail="Invalid PDF file."
            )

    elif extension == ".docx":
        if not header.startswith(b"PK\x03\x04"):
            raise HTTPException(
                status_code=400,
                detail="Invalid DOCX file."
            )

    elif extension == ".doc":
        if not header.startswith(b"\xd0\xcf\x11\xe0"):
            raise HTTPException(
                status_code=400,
                detail="Invalid DOC file."
            )


def upload_s3_file_object(bucket_name:str, file:UploadFile,project_id:uuid.UUID)->dict[str,str]:
    validate_document(file)
    key = (
            f"projects/{project_id}/"
            f"{uuid.uuid4()}_{file.filename}"
        )
    s3.upload_fileobj(
         file.file,
         bucket_name,
         key)
    return key

def get_s3_doc_url_download(bucket_name:str,key:str)->str:
    url=s3.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': bucket_name,
            'Key': key
        },
        ExpiresIn=3600
    )
    return url

def update_s3_file_object(
        bucket_name:str,
        file:UploadFile,
        key:str)->None:

    validate_document(file)
    s3.upload_fileobj(
        file.file,
        bucket_name,
        key
     )

def delete_s3_file_object(
    bucket_name: str,
    key: str
) -> None:
    s3.delete_object(
        Bucket=bucket_name,
        Key=key
    )







