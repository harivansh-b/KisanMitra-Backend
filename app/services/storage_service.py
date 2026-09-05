import os
import uuid

from typing import List, Optional
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ForbiddenException, NotFoundException, StorageException
from app.core.security import get_supabase_admin_client
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentResponse
from app.utils.enums import DocumentOwnerType, UserRole


class StorageService:
    @staticmethod
    def upload_file(
        db: Session,
        current_user: User,
        file: UploadFile,
        bucket: str,
        owner_type: DocumentOwnerType,
        folder: Optional[str] = None,
    ) -> Document:
        """
        Uploads a file to Supabase Storage and records metadata in the documents table.
        """
        file_ext = file.filename.split(".")[-1] if "." in file.filename else "bin"
        unique_file_name = f"{uuid.uuid4()}.{file_ext}"
        target_folder = folder or f"{owner_type.value.lower()}s/{current_user.id}"
        storage_path = f"{target_folder}/{unique_file_name}"

        # Read file contents
        contents = file.file.read()
        file_size = len(contents)

        # Upload to Supabase Storage using Admin Client
        # In test mode (TESTING=1 env var) or when using mock URL, skip actual storage upload
        is_test_mode = os.environ.get("TESTING") == "1" or "mock" in settings.SUPABASE_URL
        if not is_test_mode:
            try:
                supabase = get_supabase_admin_client()
                supabase.storage.from_(bucket).upload(
                    path=storage_path,
                    file=contents,
                    file_options={"content-type": file.content_type or "application/octet-stream"},
                )
            except Exception as e:
                raise StorageException(f"Failed to upload file to Supabase Storage: {str(e)}")
        else:
            pass  # In test/mock mode — skip actual upload, just record metadata


        # Store metadata in PostgreSQL
        doc = Document(
            owner_id=current_user.id,
            owner_type=owner_type,
            bucket=bucket,
            path=storage_path,
            file_name=file.filename or unique_file_name,
            content_type=file.content_type or "application/octet-stream",
            size=file_size,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc

    @staticmethod
    def get_document_url(document: Document, expires_in: int = 3600) -> str:
        """Generates a secure signed URL for the document."""
        try:
            supabase = get_supabase_admin_client()
            res = supabase.storage.from_(document.bucket).create_signed_url(
                path=document.path, expires_in=expires_in
            )
            if isinstance(res, dict) and "signedURL" in res:
                return res["signedURL"]
            elif hasattr(res, "get"):
                return res.get("signedURL") or res.get("signedUrl", "")
            return f"{settings.SUPABASE_URL}/storage/v1/object/sign/{document.bucket}/{document.path}"
        except Exception:
            return f"{settings.SUPABASE_URL}/storage/v1/object/public/{document.bucket}/{document.path}"

    @staticmethod
    def get_document(db: Session, document_id: str, current_user: User) -> DocumentResponse:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise NotFoundException(f"Document '{document_id}' not found")

        # Authorization: owner or admin
        if doc.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise ForbiddenException("You do not have permission to access this document.")

        url = StorageService.get_document_url(doc)
        return DocumentResponse(
            id=doc.id,
            owner_id=doc.owner_id,
            owner_type=doc.owner_type,
            bucket=doc.bucket,
            path=doc.path,
            file_name=doc.file_name,
            content_type=doc.content_type,
            size=doc.size,
            url=url,
            created_at=doc.created_at,
        )

    @staticmethod
    def delete_document(db: Session, document_id: str, current_user: User) -> None:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise NotFoundException(f"Document '{document_id}' not found")

        if doc.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise ForbiddenException("You do not have permission to delete this document.")

        try:
            supabase = get_supabase_admin_client()
            supabase.storage.from_(doc.bucket).remove([doc.path])
        except Exception:
            pass

        db.delete(doc)
        db.commit()

    @staticmethod
    def list_user_documents(db: Session, current_user: User) -> List[DocumentResponse]:
        docs = db.query(Document).filter(Document.owner_id == current_user.id).all()
        return [
            DocumentResponse(
                id=doc.id,
                owner_id=doc.owner_id,
                owner_type=doc.owner_type,
                bucket=doc.bucket,
                path=doc.path,
                file_name=doc.file_name,
                content_type=doc.content_type,
                size=doc.size,
                url=StorageService.get_document_url(doc),
                created_at=doc.created_at,
            )
            for doc in docs
        ]


storage_service = StorageService()
