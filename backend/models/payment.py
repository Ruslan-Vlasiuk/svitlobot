from sqlalchemy import Column, Integer, BigInteger, String, Numeric, DateTime
from sqlalchemy.sql import func
from database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)

    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default='UAH')

    payment_method = Column(String(20))  # 'liqpay', 'wayforpay'
    payment_id = Column(String(100), unique=True, index=True)

    status = Column(String(20), default='pending', index=True)
    # 'pending', 'success', 'failed'

    subscription_days = Column(Integer, nullable=False)
    subscription_tier = Column(String(20))  # 'STANDARD', 'PRO'

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    def __repr__(self):
        return f"<Payment {self.id} {self.amount} UAH ({self.status})>"