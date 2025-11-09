from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from database import Base


class Queue(Base):
    __tablename__ = "queues"

    queue_id = Column(Integer, primary_key=True)  # 1-12
    name = Column(String(50))  # "Черга 1"

    # Поточний стан
    is_power_on = Column(Boolean, default=True)
    last_change_at = Column(DateTime(timezone=True))
    last_change_source = Column(String(20))  # 'iot', 'crowdreport', 'manual'

    # Статистика
    total_outages = Column(Integer, default=0)
    total_uptime_minutes = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Queue {self.queue_id} ({'ON' if self.is_power_on else 'OFF'})>"