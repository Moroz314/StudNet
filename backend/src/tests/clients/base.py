import httpx
from typing import Dict, Any, Optional
from ..config import BASE_URL, TEST_EMAIL, TEST_PASSWORD


class BaseAPIClient:
    """Базовый клиент для работы с API"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.access_token: Optional[str] = None
        self.user_id: Optional[int] = None
        self.client = httpx.Client(base_url=base_url, timeout=30.0)

    def _get_mime_type(self, file_path: str) -> str:
        """Определяет MIME тип файла"""
        extension = file_path.split('.')[-1].lower() if '.' in file_path else ''
        mime_types = {
            'pdf': 'application/pdf',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'txt': 'text/plain',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        }
        return mime_types.get(extension, 'application/octet-stream')

    def get_auth_headers(self) -> Dict[str, str]:
        """Возвращает заголовки с авторизацией"""
        if not self.access_token:
            raise ValueError("Not authenticated. Call login() first.")
        return {"Authorization": f"Bearer {self.access_token}"}

    def cleanup(self):
        """Закрывает клиент"""
        self.client.close()