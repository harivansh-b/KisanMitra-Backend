from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction import TransactionCreate
from app.utils.enums import TransactionStatus, UserRole


class TransactionService:
    @staticmethod
    def get_transaction_by_id(db: Session, txn_id: str, current_user: User) -> Transaction:
        txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
        if not txn:
            raise NotFoundException(f"Transaction '{txn_id}' not found")

        if (
            txn.buyer_id != current_user.id
            and txn.seller_id != current_user.id
            and current_user.role != UserRole.ADMIN
        ):
            raise ForbiddenException("You do not have permission to view this transaction.")

        return txn

    @staticmethod
    def list_transactions(
        db: Session,
        current_user: User,
        status: Optional[TransactionStatus] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Transaction], int]:
        query = db.query(Transaction)

        if current_user.role != UserRole.ADMIN:
            query = query.filter((Transaction.buyer_id == current_user.id) | (Transaction.seller_id == current_user.id))

        if status:
            query = query.filter(Transaction.status == status)

        total = query.count()
        txns = query.order_by(Transaction.created_at.desc()).offset(offset).limit(limit).all()
        return txns, total

    @staticmethod
    def create_transaction(db: Session, current_user: User, data: TransactionCreate) -> Transaction:
        # Authorization check: user must be buyer, seller, or admin
        if (
            current_user.id != data.buyer_id
            and current_user.id != data.seller_id
            and current_user.role != UserRole.ADMIN
        ):
            raise ForbiddenException("Unauthorized to create transaction for other participants.")

        total_amount = round(data.quantity * data.price_per_unit, 2)
        txn = Transaction(
            order_id=data.order_id,
            buyer_id=data.buyer_id,
            seller_id=data.seller_id,
            listing_id=data.listing_id,
            quantity=data.quantity,
            price_per_unit=data.price_per_unit,
            total_amount=total_amount,
            status=TransactionStatus.INITIATED,
            notes=data.notes,
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)
        return txn


transaction_service = TransactionService()
