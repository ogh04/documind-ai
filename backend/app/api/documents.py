import logging
import time
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.config import settings
from app.core.logging_config import get_logger, log_event
from app.database.database import get_db
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.user import User
from app.schemas.document import DocumentRead
from app.schemas.document_chunk import DocumentChunkRead
from app.services.chunking_service import create_chunks_from_extracted_text
from app.services.embedding_service import embed_passages
from app.services.extraction_service import (
    extract_text_from_document,
    validate_file_exists,
)
from app.services.qdrant_service import upsert_document_chunks_to_qdrant


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)

logger = get_logger(__name__)


DOCUMENT_STATUS_UPLOADED = "uploaded"
DOCUMENT_STATUS_PROCESSING = "processing"
DOCUMENT_STATUS_PROCESSED = "processed"
DOCUMENT_STATUS_INDEXED = "indexed"
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


PROCESSABLE_FILE_TYPES = {
    "pdf",
    "docx",
    "png",
    "jpg",
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
    start_time = time.perf_counter()

    try:
        if not file.filename:
            log_event(
                logger=logger,
                event="upload_rejected",
                message="Upload rejected because no file was provided",
                level=logging.WARNING,
                user_id=current_user.id,
                reason="missing_filename",
            )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided",
            )

        original_filename = Path(file.filename).name
        file_extension = Path(original_filename).suffix.lower()

        log_event(
            logger=logger,
            event="upload_started",
            message="Document upload started",
            user_id=current_user.id,
            original_filename=original_filename,
            file_extension=file_extension,
            content_type=file.content_type,
        )

        if file_extension not in ALLOWED_EXTENSIONS:
            log_event(
                logger=logger,
                event="upload_rejected",
                message="Upload rejected because file extension is unsupported",
                level=logging.WARNING,
                user_id=current_user.id,
                original_filename=original_filename,
                file_extension=file_extension,
                reason="unsupported_extension",
            )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file type. Allowed types: PDF, DOCX, PNG, JPG",
            )

        if file.content_type not in ALLOWED_CONTENT_TYPES:
            log_event(
                logger=logger,
                event="upload_rejected",
                message="Upload rejected because content type is invalid",
                level=logging.WARNING,
                user_id=current_user.id,
                original_filename=original_filename,
                content_type=file.content_type,
                reason="invalid_content_type",
            )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file content type",
            )

        file_content = await file.read()
        file_size = len(file_content)

        max_file_size = settings.max_upload_size_mb * 1024 * 1024

        if file_size > max_file_size:
            log_event(
                logger=logger,
                event="upload_rejected",
                message="Upload rejected because file is too large",
                level=logging.WARNING,
                user_id=current_user.id,
                original_filename=original_filename,
                file_size=file_size,
                max_file_size=max_file_size,
                reason="file_too_large",
            )

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

        duration_ms = (time.perf_counter() - start_time) * 1000

        log_event(
            logger=logger,
            event="upload_completed",
            message="Document upload completed",
            user_id=current_user.id,
            document_id=document.id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_type=document.file_type,
            file_size=file_size,
            duration_ms=round(duration_ms, 2),
        )

        return document

    except HTTPException:
        raise

    except Exception:
        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.exception(
            "Document upload failed",
            extra={
                "event": "upload_failed",
                "extra_fields": {
                    "user_id": current_user.id,
                    "duration_ms": round(duration_ms, 2),
                },
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document upload failed.",
        )


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


@router.get("/{document_id}/chunks", response_model=list[DocumentChunkRead])
def get_document_chunks(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_user_document(
        document_id=document_id,
        db=db,
        current_user=current_user,
    )

    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document.id)
        .order_by(DocumentChunk.chunk_index.asc())
        .all()
    )

    return chunks


@router.post("/{document_id}/index")
def index_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    start_time = time.perf_counter()

    document = get_user_document(
        document_id=document_id,
        db=db,
        current_user=current_user,
    )

    log_event(
        logger=logger,
        event="indexing_started",
        message="Document indexing started",
        user_id=current_user.id,
        document_id=document.id,
        original_filename=document.original_filename,
        status=document.status,
    )

    if document.status not in {
        DOCUMENT_STATUS_PROCESSED,
        DOCUMENT_STATUS_INDEXED,
    }:
        log_event(
            logger=logger,
            event="indexing_rejected",
            message="Document indexing rejected because document is not processed",
            level=logging.WARNING,
            user_id=current_user.id,
            document_id=document.id,
            status=document.status,
            reason="document_not_processed",
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document must be processed before indexing.",
        )

    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document.id)
        .order_by(DocumentChunk.chunk_index.asc())
        .all()
    )

    if not chunks:
        log_event(
            logger=logger,
            event="indexing_rejected",
            message="Document indexing rejected because no chunks were found",
            level=logging.WARNING,
            user_id=current_user.id,
            document_id=document.id,
            reason="no_chunks_found",
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No chunks found for this document. Process the document first.",
        )

    try:
        embedding_start_time = time.perf_counter()

        chunk_texts = [
            chunk.text
            for chunk in chunks
        ]

        embeddings = embed_passages(chunk_texts)

        embedding_duration_ms = (
            time.perf_counter() - embedding_start_time
        ) * 1000

        log_event(
            logger=logger,
            event="embedding_completed",
            message="Chunk embedding completed before indexing",
            user_id=current_user.id,
            document_id=document.id,
            chunk_count=len(chunks),
            embedding_count=len(embeddings),
            embedding_provider=settings.embedding_provider,
            embedding_model=settings.embedding_model_name,
            duration_ms=round(embedding_duration_ms, 2),
        )

        qdrant_start_time = time.perf_counter()

        indexed_count = upsert_document_chunks_to_qdrant(
            document=document,
            chunks=chunks,
            embeddings=embeddings,
            user_id=current_user.id,
        )

        qdrant_duration_ms = (
            time.perf_counter() - qdrant_start_time
        ) * 1000

        document.status = DOCUMENT_STATUS_INDEXED
        db.commit()
        db.refresh(document)

        total_duration_ms = (time.perf_counter() - start_time) * 1000

        log_event(
            logger=logger,
            event="indexing_completed",
            message="Document indexing completed",
            user_id=current_user.id,
            document_id=document.id,
            indexed_chunks=indexed_count,
            collection=settings.qdrant_collection_name,
            vector_size=settings.embedding_vector_size,
            qdrant_duration_ms=round(qdrant_duration_ms, 2),
            total_duration_ms=round(total_duration_ms, 2),
        )

        return {
            "document_id": document.id,
            "original_filename": document.original_filename,
            "status": DOCUMENT_STATUS_INDEXED,
            "indexed_chunks": indexed_count,
            "collection": settings.qdrant_collection_name,
            "embedding_provider": settings.embedding_provider,
            "embedding_model": settings.embedding_model_name,
            "vector_size": settings.embedding_vector_size,
            "message": "Document chunks indexed successfully in Qdrant.",
        }

    except Exception:
        total_duration_ms = (time.perf_counter() - start_time) * 1000

        logger.exception(
            "Document indexing failed",
            extra={
                "event": "indexing_failed",
                "extra_fields": {
                    "user_id": current_user.id,
                    "document_id": document.id,
                    "duration_ms": round(total_duration_ms, 2),
                },
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document indexing failed.",
        )


@router.post("/{document_id}/process")
def process_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    start_time = time.perf_counter()

    document = get_user_document(
        document_id=document_id,
        db=db,
        current_user=current_user,
    )

    log_event(
        logger=logger,
        event="document_processing_started",
        message="Document processing started",
        user_id=current_user.id,
        document_id=document.id,
        original_filename=document.original_filename,
        file_type=document.file_type,
    )

    document.status = DOCUMENT_STATUS_PROCESSING
    db.commit()
    db.refresh(document)

    try:
        if document.file_type not in PROCESSABLE_FILE_TYPES:
            document.status = DOCUMENT_STATUS_FAILED
            db.commit()

            log_event(
                logger=logger,
                event="document_processing_rejected",
                message="Document processing rejected because file type is not processable",
                level=logging.WARNING,
                user_id=current_user.id,
                document_id=document.id,
                file_type=document.file_type,
                reason="unsupported_processing_file_type",
            )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Processing is currently supported only for PDF, DOCX, PNG, and JPG files."
                ),
            )

        validate_file_exists(document.file_path)

        extraction_start_time = time.perf_counter()

        extracted_text = extract_text_from_document(
            file_path=document.file_path,
            file_type=document.file_type,
        )

        extraction_duration_ms = (
            time.perf_counter() - extraction_start_time
        ) * 1000

        log_event(
            logger=logger,
            event="extraction_completed",
            message="Document text extraction completed",
            user_id=current_user.id,
            document_id=document.id,
            file_type=document.file_type,
            text_length=len(extracted_text or ""),
            duration_ms=round(extraction_duration_ms, 2),
        )

        if not extracted_text:
            document.status = DOCUMENT_STATUS_FAILED
            db.commit()

            total_duration_ms = (time.perf_counter() - start_time) * 1000

            log_event(
                logger=logger,
                event="document_processing_failed",
                message="Document processing failed because no text was extracted",
                level=logging.WARNING,
                user_id=current_user.id,
                document_id=document.id,
                reason="empty_extracted_text",
                total_duration_ms=round(total_duration_ms, 2),
            )

            return {
                "document_id": document.id,
                "original_filename": document.original_filename,
                "file_type": document.file_type,
                "status": DOCUMENT_STATUS_FAILED,
                "text_length": 0,
                "chunk_count": 0,
                "message": "No text could be extracted from this document.",
                "extracted_text": "",
            }

        chunking_start_time = time.perf_counter()

        text_chunks = create_chunks_from_extracted_text(extracted_text)

        chunking_duration_ms = (
            time.perf_counter() - chunking_start_time
        ) * 1000

        log_event(
            logger=logger,
            event="chunking_completed",
            message="Document chunking completed",
            user_id=current_user.id,
            document_id=document.id,
            text_length=len(extracted_text),
            chunk_count=len(text_chunks),
            duration_ms=round(chunking_duration_ms, 2),
        )

        if not text_chunks:
            document.status = DOCUMENT_STATUS_FAILED
            db.commit()

            total_duration_ms = (time.perf_counter() - start_time) * 1000

            log_event(
                logger=logger,
                event="document_processing_failed",
                message="Document processing failed because no chunks were created",
                level=logging.WARNING,
                user_id=current_user.id,
                document_id=document.id,
                reason="empty_chunks",
                total_duration_ms=round(total_duration_ms, 2),
            )

            return {
                "document_id": document.id,
                "original_filename": document.original_filename,
                "file_type": document.file_type,
                "status": DOCUMENT_STATUS_FAILED,
                "text_length": len(extracted_text),
                "chunk_count": 0,
                "message": "Text was extracted, but no chunks could be created.",
                "extracted_text": extracted_text,
            }

        db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document.id
        ).delete(synchronize_session=False)

        chunk_records = [
            DocumentChunk(
                document_id=document.id,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
            )
            for chunk in text_chunks
        ]

        db.add_all(chunk_records)

        document.status = DOCUMENT_STATUS_PROCESSED
        db.commit()
        db.refresh(document)

        total_duration_ms = (time.perf_counter() - start_time) * 1000

        log_event(
            logger=logger,
            event="document_processing_completed",
            message="Document processing completed",
            user_id=current_user.id,
            document_id=document.id,
            text_length=len(extracted_text),
            chunk_count=len(chunk_records),
            total_duration_ms=round(total_duration_ms, 2),
        )

        return {
            "document_id": document.id,
            "original_filename": document.original_filename,
            "file_type": document.file_type,
            "status": DOCUMENT_STATUS_PROCESSED,
            "text_length": len(extracted_text),
            "chunk_count": len(chunk_records),
            "message": "Document processed and chunked successfully.",
            "extracted_text": extracted_text,
        }

    except HTTPException:
        raise

    except Exception:
        document.status = DOCUMENT_STATUS_FAILED
        db.commit()

        total_duration_ms = (time.perf_counter() - start_time) * 1000

        logger.exception(
            "Document processing failed",
            extra={
                "event": "document_processing_failed",
                "extra_fields": {
                    "user_id": current_user.id,
                    "document_id": document.id,
                    "duration_ms": round(total_duration_ms, 2),
                },
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document processing failed.",
        )