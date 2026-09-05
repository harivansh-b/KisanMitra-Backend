from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    InvalidStateTransitionException,
    NotFoundException,
)
from app.models.order import Order
from app.models.produce_listing import ProduceListing
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.order import OrderCreate, OrderStatusUpdate
from app.utils.enums import ListingStatus, OrderStatus, TransactionStatus, UserRole


class OrderService:
    @staticmethod
    def get_order_by_id(db: Session, order_id: str, current_user: User) -> Order:
        order = (
            db.query(Order)
            .options(
                joinedload(Order.listing).joinedload(ProduceListing.crop),
                joinedload(Order.transactions),
            )
            .filter(Order.id == order_id)
            .first()
        )
        if not order:
            raise NotFoundException(f"Order '{order_id}' not found")

        # Authorization: user must be buyer, seller, or admin
        if (
            order.buyer_id != current_user.id
            and order.seller_id != current_user.id
            and current_user.role != UserRole.ADMIN
        ):
            raise ForbiddenException("You do not have permission to view this order.")

        return order

    @staticmethod
    def create_order(db: Session, buyer: User, data: OrderCreate) -> Order:
        if buyer.role != UserRole.BUYER and buyer.role != UserRole.ADMIN:
            raise ForbiddenException("Only registered buyers can place purchase requests.")

        listing = db.query(ProduceListing).filter(ProduceListing.id == data.listing_id).first()
        if not listing:
            raise NotFoundException(f"Listing '{data.listing_id}' not found")

        if listing.status != ListingStatus.ACTIVE:
            raise BadRequestException(f"Listing is not currently active (status: {listing.status.value}).")

        if listing.seller_id == buyer.id:
            raise BadRequestException("You cannot place an order on your own listing.")

        if data.quantity > listing.quantity:
            raise BadRequestException(
                f"Requested quantity ({data.quantity}) exceeds available listing quantity ({listing.quantity})."
            )

        agreed_price = data.agreed_price or listing.expected_price
        if listing.min_price and agreed_price < listing.min_price:
            raise BadRequestException(f"Offered price ({agreed_price}) is below seller's minimum price ({listing.min_price}).")

        total_amount = round(data.quantity * agreed_price, 2)

        order = Order(
            buyer_id=buyer.id,
            seller_id=listing.seller_id,
            listing_id=listing.id,
            quantity=data.quantity,
            agreed_price=agreed_price,
            total_amount=total_amount,
            status=OrderStatus.PENDING,
            delivery_location=data.delivery_location or listing.location_name,
            notes=data.notes,
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def update_order_status(db: Session, order_id: str, current_user: User, data: OrderStatusUpdate) -> Order:
        order = OrderService.get_order_by_id(db, order_id, current_user)
        new_status = data.status
        curr_status = order.status

        # Prevent modifications to terminal states
        if curr_status in [OrderStatus.COMPLETED, OrderStatus.REJECTED, OrderStatus.CANCELLED]:
            raise InvalidStateTransitionException(curr_status.value, new_status.value, "Order")

        is_buyer = order.buyer_id == current_user.id
        is_seller = order.seller_id == current_user.id
        is_admin = current_user.role == UserRole.ADMIN

        # Transition validation
        if curr_status == OrderStatus.PENDING:
            if new_status == OrderStatus.ACCEPTED:
                if not (is_seller or is_admin):
                    raise ForbiddenException("Only the seller can accept a pending purchase request.")
            elif new_status == OrderStatus.REJECTED:
                if not (is_seller or is_admin):
                    raise ForbiddenException("Only the seller can reject a pending purchase request.")
            elif new_status == OrderStatus.CANCELLED:
                if not (is_buyer or is_admin):
                    raise ForbiddenException("Only the buyer can cancel their pending purchase request.")
            else:
                raise InvalidStateTransitionException(curr_status.value, new_status.value, "Order")

        elif curr_status == OrderStatus.ACCEPTED:
            if new_status == OrderStatus.CONFIRMED:
                if not (is_buyer or is_seller or is_admin):
                    raise ForbiddenException("Unauthorized to confirm this order.")
                # When order is confirmed, record transaction ledger entry
                transaction = Transaction(
                    order_id=order.id,
                    buyer_id=order.buyer_id,
                    seller_id=order.seller_id,
                    listing_id=order.listing_id,
                    quantity=order.quantity,
                    price_per_unit=order.agreed_price,
                    total_amount=order.total_amount,
                    status=TransactionStatus.INITIATED,
                    notes=f"Transaction initiated upon order confirmation for Order #{order.id}",
                )
                db.add(transaction)
            elif new_status == OrderStatus.CANCELLED:
                if not (is_buyer or is_admin):
                    raise ForbiddenException("Only the buyer can cancel an accepted order before confirmation.")
            else:
                raise InvalidStateTransitionException(curr_status.value, new_status.value, "Order")

        elif curr_status == OrderStatus.CONFIRMED:
            if new_status == OrderStatus.COMPLETED:
                if not (is_buyer or is_seller or is_admin):
                    raise ForbiddenException("Unauthorized to complete this order.")
                # Mark linked transaction as SETTLED
                for txn in order.transactions:
                    if txn.status == TransactionStatus.INITIATED:
                        txn.status = TransactionStatus.SETTLED
            elif new_status == OrderStatus.CANCELLED:
                if not is_admin:
                    raise ForbiddenException("Confirmed orders can only be cancelled by an administrator.")
                for txn in order.transactions:
                    txn.status = TransactionStatus.REFUNDED
            else:
                raise InvalidStateTransitionException(curr_status.value, new_status.value, "Order")

        order.status = new_status
        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def list_orders(
        db: Session,
        current_user: User,
        status: Optional[OrderStatus] = None,
        as_role: Optional[str] = None,  # "buyer" or "seller"
        offset: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Order], int]:
        query = (
            db.query(Order)
            .options(joinedload(Order.listing).joinedload(ProduceListing.crop))
        )

        if as_role == "buyer":
            query = query.filter(Order.buyer_id == current_user.id)
        elif as_role == "seller":
            query = query.filter(Order.seller_id == current_user.id)
        else:
            query = query.filter((Order.buyer_id == current_user.id) | (Order.seller_id == current_user.id))

        if status:
            query = query.filter(Order.status == status)

        total = query.count()
        orders = query.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()
        return orders, total


order_service = OrderService()
