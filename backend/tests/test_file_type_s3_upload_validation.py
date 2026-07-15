from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile

from backend.utils.s3_utils import validate_document



def test_validate_document_pdf_valid() -> None:
    file = UploadFile(
        filename="document.pdf",
        file=BytesIO(
            b"%PDF-1.4 fake pdf content"
        )
    )

    validate_document(file)

    assert file.filename == "document.pdf"


def test_validate_document_invalid_extension() -> None:
    file = UploadFile(
        filename="image.png",
        file=BytesIO(
            b"fake image"
        )
    )

    with pytest.raises(HTTPException) as exc:
        validate_document(file)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Only PDF, DOC and DOCX files are allowed."


@pytest.mark.parametrize(
    "filename,content,expected_detail",
    [
        ("a.pdf", b"BADDATA", "Invalid PDF file."),
        ("a.docx", b"BADDATA", "Invalid DOCX file."),
        ("a.doc", b"BADDATA", "Invalid DOC file."),
    ],
)
def test_validate_document_invalid_signature(
    filename: str,
    content: bytes,
    expected_detail: str,
) -> None:
    file = UploadFile(
        filename=filename,
        file=BytesIO(content),
    )

    with pytest.raises(HTTPException) as exc:
        validate_document(file)

    assert exc.value.status_code == 400
    assert exc.value.detail == expected_detail

