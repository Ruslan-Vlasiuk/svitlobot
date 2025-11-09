from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint, BigInteger
from sqlalchemy.sql import func
from database import Base


class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    street = Column(String(200), nullable=False, index=True)
    house_number = Column(String(20), nullable=False)
    queue_id = Column(Integer, nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    added_by = Column(String(20), default='admin')  # 'admin', 'user', 'auto'

    __table_args__ = (
        UniqueConstraint('street', 'house_number', name='uix_street_house'),
    )

    def __repr__(self):
        return f"<Address {self.street} {self.house_number} (Q{self.queue_id})>"


class UserAddress(Base):
    """Зв'язок користувачів та адрес (для PRO з 3 адресами)"""
    __tablename__ = "user_addresses"

    user_id = Column(BigInteger, primary_key=True)
    address_id = Column(Integer, primary_key=True)
    priority = Column(Integer, default=1)  # 1, 2, 3

    def __repr__(self):
        return f"<UserAddress user={self.user_id} addr={self.address_id}>"