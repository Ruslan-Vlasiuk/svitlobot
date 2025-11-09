from sqlalchemy import Column, Integer, String, Boolean, Numeric, DateTime
from sqlalchemy.sql import func
from database import Base


class IoTSensor(Base):
    __tablename__ = "iot_sensors"

    sensor_id = Column(String(50), primary_key=True)  # "ESP32_001"
    queue_id = Column(Integer, nullable=False, index=True)
    priority = Column(Integer, nullable=False)  # 1 або 2

    # Статус
    is_online = Column(Boolean, default=False)
    last_ping_at = Column(DateTime(timezone=True))

    # Технічні дані
    firmware_version = Column(String(20))
    ip_address = Column(String(45))
    sim_card = Column(String(20))

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<IoTSensor {self.sensor_id} Q{self.queue_id}>"


class IoTData(Base):
    """Дані від сенсорів"""
    __tablename__ = "iot_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sensor_id = Column(String(50), nullable=False, index=True)

    is_power_on = Column(Boolean, nullable=False)
    voltage = Column(Numeric(5, 2))  # PRO
    frequency = Column(Numeric(5, 2))  # PRO

    received_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self):
        return f"<IoTData {self.sensor_id} {'ON' if self.is_power_on else 'OFF'}>"