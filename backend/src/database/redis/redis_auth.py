from .base_redis import RedisInit
import os
from dotenv import load_dotenv
import json
from datetime import timedelta
import secrets

load_dotenv()

VERIFICATION_CODE_EXPIRE_MINUTES = float(os.getenv("VERIFICATION_CODE_EXPIRE_MINUTES"))

class RedisAuth(RedisInit):
    async def store_verification_data(self, email: str, user_data: dict, code: str) -> None:
        """Сохраняем данные пользователя и код в Redis"""
        key = f"verification:{email}"
        data = {
            'user_data': user_data,  # email и хэш пароля
            'code': code,
            'attempts': 0  # счетчик попыток ввода кода
        }

        await self.redis.setex(
            key,
            timedelta(minutes=VERIFICATION_CODE_EXPIRE_MINUTES),
            json.dumps(data)
        )

    async def get_verification_data(self, email: str) -> dict:
        # Получаем данные верификации из Redis
        key = f"verification:{email}"
        data = await self.redis.get(key)
        return json.loads(data) if data else None

    async def delete_verification_data(self, email: str) -> None:
        # Удаляем данные верификации после успешной проверки
        key = f"verification:{email}"
        await self.redis.delete(key)

    async def increment_attempts(self, email: str) -> int:
        # Увеличиваем счетчик попыток
        key = f"verification:{email}"
        data = await self.get_verification_data(email)
        if data:
            data['attempts'] += 1
            ttl = await self.redis.ttl(key)
            await self.redis.setex(key, timedelta(seconds=ttl), json.dumps(data))
            return data['attempts']
        return 0

    async def is_rate_limited(self, email: str, max_attempts: int = 5) -> bool:
        # Проверяем, не превышено ли количество попыток
        data = await self.get_verification_data(email)
        return data and data.get('attempts', 0) >= max_attempts

    @staticmethod
    def generate_code(length: int = 6) -> str:
        # Генерация случайного цифрового кода
        return ''.join(secrets.choice('0123456789') for _ in range(length))