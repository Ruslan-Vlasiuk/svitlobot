from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

from database import get_db
from models.iot_sensor import IoTSensor, IoTData
from config import settings

router = APIRouter(prefix="/api/iot", tags=["IoT"])


# ============================================
# AUTHENTICATION
# ============================================

async def verify_iot_key(x_iot_key: str = Header(...)):
    """Проверка API ключа от IoT устройства"""
    if x_iot_key != settings.IOT_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid IoT API key"
        )
    return True


# ============================================
# PYDANTIC SCHEMAS
# ============================================

class IoTDataReceive(BaseModel):
    sensor_id: str
    is_power_on: bool
    voltage: Optional[float] = None  # PRO sensors
    frequency: Optional[float] = None  # PRO sensors


class IoTSensorCreate(BaseModel):
    sensor_id: str
    queue_id: int
    priority: int  # 1 или 2
    firmware_version: Optional[str] = None
    ip_address: Optional[str] = None
    sim_card: Optional[str] = None


class IoTSensorResponse(BaseModel):
    sensor_id: str
    queue_id: int
    priority: int
    is_online: bool
    last_ping_at: Optional[datetime]
    firmware_version: Optional[str]
    
    class Config:
        from_attributes = True


# ============================================
# ENDPOINTS
# ============================================

@router.post("/data", dependencies=[Depends(verify_iot_key)])
async def receive_iot_data(
    data: IoTDataReceive,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить данные от IoT сенсора
    
    **Вызывается ESP32 каждые 10-30 секунд**
    
    Формат запроса:
    ```
    POST /api/iot/data
    Headers: X-IoT-Key: your_iot_api_key
    Body: {
        "sensor_id": "ESP32_CH5_01",
        "is_power_on": true,
        "voltage": 224.5,
        "frequency": 50.1
    }
    ```
    """
    
    # 1. Обновить статус сенсора
    result = await db.execute(
        select(IoTSensor).where(IoTSensor.sensor_id == data.sensor_id)
    )
    sensor = result.scalar_one_or_none()
    
    if not sensor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sensor {data.sensor_id} not found"
        )
    
    sensor.is_online = True
    sensor.last_ping_at = datetime.utcnow()
    
    # 2. Сохранить данные
    iot_data = IoTData(
        sensor_id=data.sensor_id,
        is_power_on=data.is_power_on,
        voltage=data.voltage,
        frequency=data.frequency
    )
    
    db.add(iot_data)
    
    # 3. Проверить изменение статуса черги
    from models.queue import Queue
    result = await db.execute(
        select(Queue).where(Queue.queue_id == sensor.queue_id)
    )
    queue = result.scalar_one_or_none()
    
    if not queue:
        await db.commit()
        return {"status": "received", "message": "Data saved, but queue not found"}
    
    # Текущий статус черги
    current_status = queue.is_power_on
    new_status = data.is_power_on
    
    # 4. Логика подтверждения (2 сенсора)
    status_changed = False
    
    if current_status != new_status:
        # Статус изменился - проверить второй сенсор
        other_sensor = await get_other_sensor(db, sensor.queue_id, data.sensor_id)
        
        if other_sensor:
            # Есть второй сенсор - проверить его последние данные
            other_data = await get_latest_sensor_data(db, other_sensor.sensor_id)
            
            if other_data and other_data.is_power_on == new_status:
                # ✅ Оба сенсора подтверждают изменение
                queue.is_power_on = new_status
                queue.last_change_at = datetime.utcnow()
                queue.last_change_source = 'iot'
                
                if not new_status:
                    queue.total_outages += 1
                
                status_changed = True
                
                # TODO: Trigger notification
                # from tasks.notification_dispatcher import send_power_notification
                # send_power_notification.delay(sensor.queue_id, new_status)
            else:
                # ⏳ Только один сенсор сообщил об изменении
                # Ждём подтверждения от второго (в следующем ping)
                pass
        else:
            # Нет второго сенсора - принимаем данные от одного
            queue.is_power_on = new_status
            queue.last_change_at = datetime.utcnow()
            queue.last_change_source = 'iot'
            status_changed = True
    
    await db.commit()
    
    return {
        "status": "received",
        "sensor_id": data.sensor_id,
        "queue_id": sensor.queue_id,
        "power_status": "ON" if data.is_power_on else "OFF",
        "status_changed": status_changed
    }


@router.get("/sensors", response_model=list[IoTSensorResponse])
async def get_all_sensors(
    queue_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список всех IoT сенсоров
    
    Можно фильтровать по queue_id
    """
    query = select(IoTSensor).order_by(IoTSensor.queue_id, IoTSensor.priority)
    
    if queue_id:
        query = query.where(IoTSensor.queue_id == queue_id)
    
    result = await db.execute(query)
    sensors = result.scalars().all()
    
    return sensors


@router.get("/sensors/{sensor_id}")
async def get_sensor_details(
    sensor_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Подробная информация о сенсоре
    """
    result = await db.execute(
        select(IoTSensor).where(IoTSensor.sensor_id == sensor_id)
    )
    sensor = result.scalar_one_or_none()
    
    if not sensor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sensor {sensor_id} not found"
        )
    
    # Последние 10 записей данных
    result = await db.execute(
        select(IoTData)
        .where(IoTData.sensor_id == sensor_id)
        .order_by(IoTData.received_at.desc())
        .limit(10)
    )
    recent_data = result.scalars().all()
    
    return {
        "sensor": sensor,
        "recent_data": [
            {
                "is_power_on": d.is_power_on,
                "voltage": d.voltage,
                "frequency": d.frequency,
                "received_at": d.received_at
            }
            for d in recent_data
        ]
    }


@router.post("/sensors", response_model=IoTSensorResponse)
async def register_sensor(
    sensor_data: IoTSensorCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Зарегистрировать новый IoT сенсор
    
    Используется при настройке ESP32
    """
    # Проверить, существует ли сенсор
    result = await db.execute(
        select(IoTSensor).where(IoTSensor.sensor_id == sensor_data.sensor_id)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        return existing
    
    # Создать новый сенсор
    sensor = IoTSensor(
        sensor_id=sensor_data.sensor_id,
        queue_id=sensor_data.queue_id,
        priority=sensor_data.priority,
        firmware_version=sensor_data.firmware_version,
        ip_address=sensor_data.ip_address,
        sim_card=sensor_data.sim_card,
        is_online=False
    )
    
    db.add(sensor)
    await db.commit()
    await db.refresh(sensor)
    
    return sensor


@router.get("/health-check")
async def check_sensors_health(
    db: AsyncSession = Depends(get_db)
):
    """
    Проверка здоровья всех сенсоров
    
    Используется для:
    - Мониторинга
    - Алертов админу
    """
    result = await db.execute(select(IoTSensor))
    sensors = result.scalars().all()
    
    online_count = 0
    offline_sensors = []
    
    threshold = datetime.utcnow() - timedelta(minutes=5)
    
    for sensor in sensors:
        if sensor.last_ping_at and sensor.last_ping_at > threshold:
            online_count += 1
        else:
            offline_sensors.append({
                "sensor_id": sensor.sensor_id,
                "queue_id": sensor.queue_id,
                "last_ping": sensor.last_ping_at
            })
    
    return {
        "total_sensors": len(sensors),
        "online": online_count,
        "offline": len(offline_sensors),
        "offline_sensors": offline_sensors,
        "health": "healthy" if len(offline_sensors) == 0 else "degraded"
    }


# ============================================
# HELPER FUNCTIONS
# ============================================

async def get_other_sensor(db: AsyncSession, queue_id: int, current_sensor_id: str):
    """Получить второй сенсор черги"""
    result = await db.execute(
        select(IoTSensor).where(
            IoTSensor.queue_id == queue_id,
            IoTSensor.sensor_id != current_sensor_id
        )
    )
    return result.scalar_one_or_none()


async def get_latest_sensor_data(db: AsyncSession, sensor_id: str):
    """Получить последние данные от сенсора (за последние 60 сек)"""
    threshold = datetime.utcnow() - timedelta(seconds=60)
    
    result = await db.execute(
        select(IoTData)
        .where(
            IoTData.sensor_id == sensor_id,
            IoTData.received_at > threshold
        )
        .order_by(IoTData.received_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
