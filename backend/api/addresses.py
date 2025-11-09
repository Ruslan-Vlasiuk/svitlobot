from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from typing import List, Optional
from pydantic import BaseModel
from rapidfuzz import fuzz, process


from database import get_db
from models.address import Address

router = APIRouter(prefix="/api/addresses", tags=["Addresses"])


# ============================================
# HELPER FUNCTIONS
# ============================================

def normalize_street_for_search(text: str) -> str:
    """
    Нормализует название улицы для поиска
    Убирает дефисы, пробелы, приводит к нижнему регистру

    Примеры:
    "Ново-Оскільська" -> "новооскільська"
    "Ново Оскільська" -> "новооскільська"
    """
    text = text.lower().strip()
    text = text.replace('-', '')  # Убрать дефисы
    text = text.replace(' ', '')  # Убрать пробелы внутри
    text = text.replace('ё', 'е')
    return text


# ============================================
# PYDANTIC SCHEMAS
# ============================================

class AddressCreate(BaseModel):
    street: str
    house_number: str
    queue_id: int


class AddressResponse(BaseModel):
    id: int
    street: str
    house_number: str
    queue_id: int
    added_by: str

    class Config:
        from_attributes = True


# ============================================
# ENDPOINTS
# ============================================

@router.get("/search", response_model=List[AddressResponse])
async def search_addresses(
        street: Optional[str] = Query(None, description="Название улицы (частичное совпадение)"),
        house_number: Optional[str] = Query(None, description="Номер дома"),
        queue_id: Optional[int] = Query(None, description="Номер черги (1-12)"),
        db: AsyncSession = Depends(get_db)
):
    """
    Поиск адресов

    Можно искать по:
    - Улице (частичное совпадение)
    - Номеру дома (точное совпадение)
    - Черге
    - Комбинация параметров

    Примеры:
    - /api/addresses/search?street=Соборна
    - /api/addresses/search?street=Соборна&house_number=12
    - /api/addresses/search?queue_id=5
    """
    query = select(Address)

    filters = []

    if street:
        # Частичное совпадение (case-insensitive)
        filters.append(Address.street.ilike(f"%{street}%"))

    if house_number:
        filters.append(Address.house_number == house_number)

    if queue_id:
        if queue_id < 1 or queue_id > 12:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Queue ID must be between 1 and 12"
            )
        filters.append(Address.queue_id == queue_id)

    if filters:
        query = query.where(*filters)

    query = query.order_by(Address.street, Address.house_number)

    result = await db.execute(query)
    addresses = result.scalars().all()

    return addresses


@router.get("/exact", response_model=AddressResponse)
async def get_address_exact(
        street: str = Query(..., description="Точное название улицы"),
        house_number: str = Query(..., description="Номер дома"),
        db: AsyncSession = Depends(get_db)
):
    """
    Получить адрес по точному совпадению

    Используется для определения черги пользователя

    Пример:
    /api/addresses/exact?street=вул. Соборна&house_number=12
    """
    result = await db.execute(
        select(Address).where(
            Address.street == street,
            Address.house_number == house_number
        )
    )
    address = result.scalar_one_or_none()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Address not found: {street}, {house_number}"
        )

    return address


@router.post("/", response_model=AddressResponse, status_code=status.HTTP_201_CREATED)
async def create_address(
        address_data: AddressCreate,
        db: AsyncSession = Depends(get_db)
):
    """
    Создать новый адрес

    Используется:
    - Админом при импорте Excel
    - Автоматически при вводе пользователем (если адреса нет в БД)
    """
    # Проверить, существует ли адрес
    result = await db.execute(
        select(Address).where(
            Address.street == address_data.street,
            Address.house_number == address_data.house_number
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Адрес уже существует
        return existing

    # Создать новый адрес
    new_address = Address(
        street=address_data.street,
        house_number=address_data.house_number,
        queue_id=address_data.queue_id,
        added_by='api'
    )

    db.add(new_address)
    await db.commit()
    await db.refresh(new_address)

    return new_address


@router.get("/streets")
async def get_streets(
        prefix: Optional[str] = Query(None, description="Начало названия улицы"),
        db: AsyncSession = Depends(get_db)
):
    """
    Получить список улиц с умным поиском + исправление опечаток

    Пример:
    /api/addresses/streets?prefix=Соб

    Вернёт: ["вул. Соборна", "вул. Соборності", ...]

    Умный поиск:
    - Игнорирует префиксы (вул., пр., бул.)
    - Игнорирует дефисы (Ново-Оскільська = Новооскільська)
    - Регистронезависимый
    - Исправляет опечатки (Соьорна → Соборна)
    """
    if not prefix:
        query = select(Address.street).distinct().order_by(Address.street).limit(10)
        result = await db.execute(query)
        return [row[0] for row in result.all()]

    prefix = prefix.strip()
    prefix_norm = normalize_street_for_search(prefix)

    # 1. Сначала точный поиск
    query = select(Address.street).distinct()
    search_conditions = [
        Address.street.ilike(f"{prefix}%"),
        Address.street.ilike(f"вул. {prefix}%"),
        Address.street.ilike(f"пр. {prefix}%"),
        Address.street.ilike(f"бул. {prefix}%"),
        Address.street.ilike(f"пров. {prefix}%"),
        func.lower(
            func.replace(
                func.replace(Address.street, '-', ''),
                ' ', ''
            )
        ).like(f"%{prefix_norm}%")
    ]

    query = query.where(or_(*search_conditions)).limit(20)
    result = await db.execute(query)
    streets = [row[0] for row in result.all()]

    # 2. Если ничего не найдено - нечёткий поиск
    if not streets:
        # Получить ВСЕ улицы
        all_streets_query = select(Address.street).distinct()
        all_result = await db.execute(all_streets_query)
        all_streets = [row[0] for row in all_result.all()]

        # Убрать префиксы для сравнения
        street_names = []
        for street in all_streets:
            # Убираем "вул. ", "пр. " и т.д.
            name = street
            for pref in ['вул. ', 'пр. ', 'бул. ', 'пров. ']:
                if name.startswith(pref):
                    name = name[len(pref):]
                    break
            street_names.append((street, name))

        # Нечёткое сравнение
        matches = process.extract(
            prefix,
            [name for _, name in street_names],
            scorer=fuzz.ratio,
            limit=5,
            score_cutoff=60  # Минимум 60% совпадения
        )

        # Вернуть полные названия улиц
        streets = []
        for match_text, score, idx in matches:
            streets.append(street_names[idx][0])

    return streets[:10]  # Максимум 10 результатов

@router.get("/houses")
async def get_houses_on_street(
        street: str = Query(..., description="Название улицы"),
        db: AsyncSession = Depends(get_db)
):
    """
    Получить список домов на улице

    Используется после выбора улицы пользователем

    Пример:
    /api/addresses/houses?street=вул. Соборна

    Вернёт: [
        {"house_number": "1", "queue_id": 5},
        {"house_number": "2", "queue_id": 5},
        ...
    ]
    """
    result = await db.execute(
        select(Address).where(Address.street == street).order_by(Address.house_number)
    )
    addresses = result.scalars().all()

    if not addresses:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No houses found on street: {street}"
        )

    return [
        {
            "house_number": addr.house_number,
            "queue_id": addr.queue_id
        }
        for addr in addresses
    ]


@router.get("/by-queue/{queue_id}", response_model=List[AddressResponse])
async def get_addresses_by_queue(
        queue_id: int,
        db: AsyncSession = Depends(get_db)
):
    """
    Получить все адреса черги

    Используется для:
    - Админ-панели
    - Статистики
    """
    if queue_id < 1 or queue_id > 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Queue ID must be between 1 and 12"
        )

    result = await db.execute(
        select(Address)
        .where(Address.queue_id == queue_id)
        .order_by(Address.street, Address.house_number)
    )
    addresses = result.scalars().all()

    return addresses


@router.get("/stats")
async def get_address_stats(
        db: AsyncSession = Depends(get_db)
):
    """
    Статистика по адресам

    Полезно для админа
    """
    result = await db.execute(select(Address))
    addresses = result.scalars().all()

    # Подсчёт по чергам
    by_queue = {}
    for i in range(1, 13):
        by_queue[i] = 0

    for addr in addresses:
        by_queue[addr.queue_id] += 1

    # Подсчёт улиц
    streets = set(addr.street for addr in addresses)

    return {
        "total_addresses": len(addresses),
        "total_streets": len(streets),
        "by_queue": by_queue
    }