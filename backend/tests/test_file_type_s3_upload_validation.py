from io import BytesIO

import pytest
from fastapi import UploadFile,HTTPException

from backend.s3_utils import validate_document


@pytest.mark.asyncio
async def test_validate_document_pdf_valid() -> None:
    file = UploadFile(
        filename="document.pdf",
        file=BytesIO(
            b"%PDF-1.4 fake pdf content"
        )
    )

    await validate_document(file)

    assert file.filename == "document.pdf"

@pytest.mark.asyncio
async def test_validate_document_invalid_extension() -> None:
    file = UploadFile(
        filename="image.png",
        file=BytesIO(
            b"fake image"
        )
    )

    with pytest.raises(HTTPException) as exc:
        await validate_document(file)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Only PDF, DOC and DOCX files are allowed."

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "filename,content,expected_detail",
    [
        ("a.pdf", b"BADDATA", "Invalid PDF file."),
        ("a.docx", b"BADDATA", "Invalid DOCX file."),
        ("a.doc", b"BADDATA", "Invalid DOC file."),
    ],
)
async def test_validate_document_invalid_signature(
    filename: str,
    content: bytes,
    expected_detail: str,
) -> None:
    file = UploadFile(
        filename=filename,
        file=BytesIO(content),
    )

    with pytest.raises(HTTPException) as exc:
        await validate_document(file)

    assert exc.value.status_code == 400
    assert exc.value.detail == expected_detail