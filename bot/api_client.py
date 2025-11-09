import aiohttp
import logging
from typing import Optional, Dict, Any
from config import settings

logger = logging.getLogger(__name__)


class APIClient:
    """Клиент для взаимодействия с Backend API"""

    def __init__(self):
        self.base_url = settings.API_BASE_URL
        self.session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self):
        """Создаёт сессию если её нет"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def close(self):
        """Закрывает сессию"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """GET запрос к API"""
        await self._ensure_session()
        url = f"{self.base_url}{endpoint}"

        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 404:
                    # Возвращаем None вместо ошибки при 404
                    return None
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"GET request failed: {url} - {e}")
            raise

    async def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        POST запрос к API

        Args:
            endpoint: Путь endpoint
            data: Данные для отправки

        Returns:
            Ответ от API
        """
        await self._ensure_session()
        url = f"{self.base_url}{endpoint}"

        try:
            async with self.session.post(url, json=data) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"POST request failed: {url} - {e}")
            raise

    async def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        PUT запрос к API

        Args:
            endpoint: Путь endpoint
            data: Данные для обновления

        Returns:
            Ответ от API
        """
        await self._ensure_session()
        url = f"{self.base_url}{endpoint}"

        try:
            async with self.session.put(url, json=data) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"PUT request failed: {url} - {e}")
            raise

    async def patch(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        PATCH запрос к API

        Args:
            endpoint: Путь endpoint
            data: Данные для обновления

        Returns:
            Ответ от API
        """
        await self._ensure_session()
        url = f"{self.base_url}{endpoint}"

        try:
            async with self.session.patch(url, json=data) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"PATCH request failed: {url} - {e}")
            raise

    async def delete(self, endpoint: str) -> Dict[str, Any]:
        """
        DELETE запрос к API

        Args:
            endpoint: Путь endpoint

        Returns:
            Ответ от API
        """
        await self._ensure_session()
        url = f"{self.base_url}{endpoint}"

        try:
            async with self.session.delete(url) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"DELETE request failed: {url} - {e}")
            raise

        # ============= USER METHODS =============

    async def create_user(self, user_id: int, username: Optional[str] = None,
                              first_name: Optional[str] = None, referral_code_used: Optional[str] = None) -> Dict[
            str, Any]:
            """Создание нового пользователя"""
            data = {
                "user_id": user_id,
                "username": username,
                "first_name": first_name
            }
            if referral_code_used:
                data["referral_code_used"] = referral_code_used
            return await self.post("/api/users", data)

    async def get_user(self, telegram_id: int) -> Dict[str, Any]:
            """Получение пользователя по telegram_id. Raises exception если не найден."""
            response = await self.session.get(f"{self.base_url}/api/users/{telegram_id}")

            # КРИТИЧНО: Если 404 - пользователь не существует - выбросить exception
            if response.status == 404:
                raise Exception(f"User {telegram_id} not found")

            # Другие ошибки
            response.raise_for_status()

            return await response.json()

    async def check_subscription(self, telegram_id: int, is_subscribed: bool = True) -> Dict[str, Any]:
            """Проверка/обновление подписки на канал"""
            # is_subscribed передаётся как query параметр в URL
            return await self.post(
                f"/api/users/{telegram_id}/check-subscription?is_subscribed={is_subscribed}",
                data={}
            )

    # Создаём глобальный экземпляр
api_client = APIClient()