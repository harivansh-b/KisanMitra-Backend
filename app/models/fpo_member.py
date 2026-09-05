import uuid
from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.enums import FPOMemberRole, FPOMemberStatus


class FPOMember(Base):
    __tablename__ = "fpo_members"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    fpo_id = Column(String(36), ForeignKey("fpo_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    farmer_id = Column(String(36), ForeignKey("farmer_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(Enum(FPOMemberStatus), default=FPOMemberStatus.ACTIVE, nullable=False)
    membership_role = Column(Enum(FPOMemberRole), default=FPOMemberRole.MEMBER, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("fpo_id", "farmer_id", name="uq_fpo_farmer_member"),
    )

    fpo = relationship("FPOProfile", back_populates="members")
    farmer = relationship("FarmerProfile", back_populates="fpo_memberships")
