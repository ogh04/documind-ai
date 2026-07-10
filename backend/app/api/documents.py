from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.config import settings
from app.database.database import get_db
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentRead
from app.services.extraction_service import (
    extract_text_from_document,
    validate_file_exists,
)


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


DOCUMENT_STATUS_UPLOADED = "uploaded"
DOCUMENT_STATUS_PROCESSING = "processing"
DOCUMENT_STATUS_PROCESSED = "processed"
DOCUMENT_STATUS_FAILED = "failed"


ALLOWED_EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".png": "png",
    ".jpg": "jpg",
    ".jpeg": "jpg",
}


ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/png",
    "image/jpeg",
}


def get_user_document(
    document_id: int,
    db: Session,
    current_user: User,
) -> Document:
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.owner_id == current_user.id,
        )
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return document


@router.post(
    "/upload",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided",
        )

    original_filename = Path(file.filename).name
    file_extension = Path(original_filename).suffix.lower()

    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Allowed types: PDF, DOCX, PNG, JPG",
        )

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file content type",
        )

    file_content = await file.read()
    file_size = len(file_content)

    max_file_size = settings.max_upload_size_mb * 1024 * 1024

    if file_size > max_file_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {settings.max_upload_size_mb} MB",
        )

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    stored_filename = f"{uuid4().hex}{file_extension}"
    file_path = upload_dir / stored_filename

    with open(file_path, "wb") as output_file:
        output_file.write(file_content)

    document = Document(
        owner_id=current_user.id,
        filename=stored_filename,
        original_filename=original_filename,
        file_type=ALLOWED_EXTENSIONS[file_extension],
        file_path=str(file_path),
        file_size=file_size,
        status=DOCUMENT_STATUS_UPLOADED,
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return document


@router.get("/{document_id}/status")
def get_document_status(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_user_document(
        document_id=document_id,
        db=db,
        current_user=current_user,
    )

    return {
        "document_id": document.id,
        "original_filename": document.original_filename,
        "file_type": document.file_type,
        "status": document.status,
        "owner_id": document.owner_id,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }


@router.post("/{document_id}/process")
def process_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_user_document(
        document_id=document_id,
        db=db,
        current_user=current_user,
    )

    document.status = DOCUMENT_STATUS_PROCESSING
    db.commit()
    db.refresh(document)

    try:
        if document.file_type not in {"pdf", "docx"}:
            document.status = DOCUMENT_STATUS_FAILED
            db.commit()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Processing is currently supported only for PDF and DOCX files. "
                    "Images and scanned documents will be handled later with OCR."
                ),
            )

        validate_file_exists(document.file_path)

        extracted_text = extract_text_from_document(
            file_path=document.file_path,
            file_type=document.file_type,
        )

        if not extracted_text:
            document.status = DOCUMENT_STATUS_FAILED
            db.commit()

            return {
                "document_id": document.id,
                "original_filename": document.original_filename,
                "file_type": document.file_type,
                "status": DOCUMENT_STATUS_FAILED,
                "text_length": 0,
                "message": (
                    "No selectable text was found. This may be a scanned document "
                    "and will require OCR later."
                ),
                "extracted_text": "",
            }

        document.status = DOCUMENT_STATUS_PROCESSED
        db.commit()
        db.refresh(document)

        return {
            "document_id": document.id,
            "original_filename": document.original_filename,
            "file_type": document.file_type,
            "status": DOCUMENT_STATUS_PROCESSED,
            "text_length": len(extracted_text),
            "message": "Document processed successfully.",
            "extracted_text": extracted_text,
        }

    except HTTPException:
        raise

    except Exception as error:
        document.status = DOCUMENT_STATUS_FAILED
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document processing failed: {str(error)}",
        ) from error