from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models.user import User
from app.schemas.document import DocumentResponse
from app.services.storage_service import storage_service
from app.utils.enums import DocumentOwnerType

router = APIRouter(prefix="/storage", tags=["Storage & Documents"])


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_file(
    file: UploadFile = File(...),
    bucket: Optional[str] = Form(None),
    owner_type: Optional[DocumentOwnerType] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a file (produce photo, certificate, document) to Supabase Storage.
    The document metadata is saved in PostgreSQL, and a signed URL is returned.
    """
    target_bucket = bucket or settings.STORAGE_BUCKET_DOCUMENTS
    target_owner_type = owner_type or DocumentOwnerType(current_user.role.value)

    doc = storage_service.upload_file(
        db=db,
        current_user=current_user,
        file=file,
        bucket=target_bucket,
        owner_type=target_owner_type,
    )
    return storage_service.get_document(db, doc.id, current_user)


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document_url(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve document metadata with a secure signed download URL."""
    return storage_service.get_document(db, document_id, current_user)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a document from Supabase Storage and database metadata."""
    storage_service.delete_document(db, document_id, current_user)


@router.get("", response_model=List[DocumentResponse])
def list_my_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all documents and images uploaded by the current user."""
    return storage_service.list_user_documents(db, current_user)
