from sqlalchemy import Column, Integer, BigInteger, String, Numeric, DateTime
from sqlalchemy.sql import func
from database import Base


class CrowdReport(Base):
    __tablename__ = "crowdreports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    address_id = Column(Integer, nullable=False)
    queue_id = Column(Integer, nullable=False, index=True)

    report_type = Column(String(20), nullable=False)  # 'power_on', 'power_off'
    reported_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    status = Column(String(20), default='pending', index=True)
    # 'pending', 'confirmed', 'rejected'

    moderated_at = Column(DateTime(timezone=True))
    moderated_by = Column(BigInteger)

    # Додаткові дані
    latitude = Column(Numeric(9, 6))
    longitude = Column(Numeric(9, 6))

    def __repr__(self):
        return f"<CrowdReport {self.id} Q{self.queue_id} ({self.status})>"