from sqlalchemy import Column, Integer, BigInteger, DateTime
from sqlalchemy.sql import func
from database import Base


class ReferralActivation(Base):
    __tablename__ = "referral_activations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    referrer_user_id = Column(BigInteger, nullable=False, index=True)
    referred_user_id = Column(BigInteger, nullable=False, unique=True)

    days_granted = Column(Integer, nullable=False, default=5)
    activated_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Referral {self.referrer_user_id} → {self.referred_user_id}>"