from enum import Enum


class UserRole(str, Enum):
    FARMER = "FARMER"
    FPO = "FPO"
    BUYER = "BUYER"
    ADMIN = "ADMIN"


class VerificationStatus(str, Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class SellerType(str, Enum):
    FARMER = "FARMER"
    FPO = "FPO"


class UnitEnum(str, Enum):
    KG = "KG"
    QUINTAL = "QUINTAL"
    METRIC_TON = "METRIC_TON"
    CRATE = "CRATE"
    BAG = "BAG"


class QualityGrade(str, Enum):
    GRADE_A = "GRADE_A"
    GRADE_B = "GRADE_B"
    GRADE_C = "GRADE_C"
    FAQ = "FAQ"  # Fair Average Quality
    PREMIUM = "PREMIUM"
    ORGANIC = "ORGANIC"


class ListingStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    RESERVED = "RESERVED"
    SOLD = "SOLD"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class RequirementStatus(str, Enum):
    ACTIVE = "ACTIVE"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class TransactionStatus(str, Enum):
    INITIATED = "INITIATED"
    HELD_IN_ESCROW = "HELD_IN_ESCROW"
    SETTLED = "SETTLED"
    REFUNDED = "REFUNDED"
    FAILED = "FAILED"


class FPOMemberStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PENDING = "PENDING"


class FPOMemberRole(str, Enum):
    MEMBER = "MEMBER"
    BOARD_MEMBER = "BOARD_MEMBER"
    LEADER = "LEADER"
    SECRETARY = "SECRETARY"
    TREASURER = "TREASURER"


class BuyerType(str, Enum):
    WHOLESALER = "WHOLESALER"
    RETAILER = "RETAILER"
    PROCESSOR = "PROCESSOR"
    EXPORTER = "EXPORTER"
    INSTITUTIONAL = "INSTITUTIONAL"
    COMMISSION_AGENT = "COMMISSION_AGENT"


class DocumentOwnerType(str, Enum):
    FARMER = "FARMER"
    FPO = "FPO"
    BUYER = "BUYER"
    LISTING = "LISTING"
    ORDER = "ORDER"
