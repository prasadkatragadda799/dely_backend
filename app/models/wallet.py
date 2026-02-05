from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.database import Base


class Wallet(Base):
    """One wallet per user; balance in INR."""
    __tablename__ = "wallets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    balance = Column(Numeric(12, 2), default=0, nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="wallet", uselist=False)
    transactions = relationship("WalletTransaction", back_populates="wallet", cascade="all, delete-orphan", order_by="WalletTransaction.created_at.desc()")


class WalletTransaction(Base):
    """Ledger entry: credit (add money, refund) or debit (order payment, etc.)."""
    __tablename__ = "wallet_transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    wallet_id = Column(String(36), ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(20), nullable=False)  # 'credit' | 'debit'
    amount = Column(Numeric(12, 2), nullable=False)
    description = Column(String(500), nullable=True)
    remark = Column(String(500), nullable=True)
    narration = Column(String(500), nullable=True)
    order_id = Column(String(36), nullable=True, index=True)  # For order-related debits
    payment_order_id = Column(String(100), nullable=True)  # Gateway order id for add-money
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    wallet = relationship("Wallet", back_populates="transactions")
