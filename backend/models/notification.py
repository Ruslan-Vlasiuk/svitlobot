from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    queue_id = Column(Integer, nullable=False)

    notification_type = Column(String(50), nullable=False)
    # 'power_off', 'power_on', 'warning_60min', 'warning_30min', ...

    message_text = Column(Text, nullable=False)
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    is_delivered = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Notification {self.id} ({self.notification_type})>"


class Schedule(Base):
    """Графіки планових відключень"""
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    queue_id = Column(Integer, nullable=False, index=True)

    scheduled_date = Column(DateTime(timezone=True), nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)

    is_confirmed = Column(Boolean, default=False)  # Підтверджено фактом?
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Schedule Q{self.queue_id} {self.scheduled_date}>"