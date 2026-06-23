import os
import json
from typing import Dict, Any, Optional, List
from .base import BaseAPIClient
from .auth import AuthClientMixin


class FileClientMixin(AuthClientMixin):
    """Миксин для работы с файлами через универсальные эндпоинты"""

    # ========== Universal File Upload ==========

    def upload_file(
            self: BaseAPIClient,
            file_path: str,
            file_type: str,
            metadata: Optional[Dict[str, str]] = None,
            public: bool = False
    ) -> Dict[str, Any]:
        """Загрузить один файл
        POST /files/upload

        Args:
            file_path: Путь к файлу
            file_type: Тип файла (avatar, project_file, message_attachment, project_avatar,
                      user_document, announcement_file, application_file, project_post_file,
                      task_attachment, other)
            metadata: Дополнительная метаинформация в формате JSON
            public: Сделать файл публичным
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        headers.pop("Content-Type", None)  # Убираем Content-Type для multipart

        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, self._get_mime_type(file_path))}
            data = {
                "file_type": file_type,
                "public": str(public).lower()
            }
            if metadata:
                data["metadata"] = json.dumps(metadata)

            response = self.client.post(
                "/files/upload",
                files=files,
                data=data,
                headers=headers
            )

        assert response.status_code == 200, f"File upload failed: {response.text}"
        return response.json()

    def upload_multiple_files(
            self: BaseAPIClient,
            file_paths: List[str],
            file_type: str,
            metadata: Optional[Dict[str, str]] = None,
            public: bool = False
    ) -> Dict[str, Any]:
        """Загрузить несколько файлов
        POST /files/upload-multiple

        Returns:
            {
                "files": [...],
                "failed": [...],
                "total": int,
                "success_count": int,
                "failed_count": int
            }
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        headers.pop("Content-Type", None)

        files = []
        opened_files = []
        for file_path in file_paths:
            f = open(file_path, "rb")
            opened_files.append(f)
            files.append(("files", (os.path.basename(file_path), f, self._get_mime_type(file_path))))

        data = {
            "file_type": file_type,
            "public": str(public).lower()
        }
        if metadata:
            data["metadata"] = json.dumps(metadata)

        try:
            response = self.client.post(
                "/files/upload-multiple",
                files=files,
                data=data,
                headers=headers
            )
        finally:
            for f in opened_files:
                f.close()

        assert response.status_code == 200, f"Multiple files upload failed: {response.text}"
        return response.json()

    def get_file_info(self: BaseAPIClient, file_id: str) -> Dict[str, Any]:
        """Получить информацию о файле
        GET /files/{file_id}
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get(f"/files/{file_id}", headers=headers)
        assert response.status_code == 200, f"Get file info failed: {response.text}"
        return response.json()

    def delete_file(self: BaseAPIClient, file_id: str) -> Dict[str, Any]:
        """Удалить файл (только для владельца)
        DELETE /files/{file_id}
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.delete(f"/files/{file_id}", headers=headers)
        assert response.status_code == 200, f"Delete file failed: {response.text}"
        return response.json()

    def get_file_url(
            self: BaseAPIClient,
            file_id: str,
            expires_in: int = 3600
    ) -> Dict[str, Any]:
        """Получить URL для доступа к файлу
        GET /files/{file_id}/url
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {"expires_in": expires_in}
        response = self.client.get(
            f"/files/{file_id}/url",
            params=params,
            headers=headers
        )
        assert response.status_code == 200, f"Get file URL failed: {response.text}"
        return response.json()

    def get_my_files(
            self: BaseAPIClient,
            file_type: Optional[str] = None,
            limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Получить файлы текущего пользователя
        GET /files/user/my-files
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {"limit": limit}
        if file_type:
            params["file_type"] = file_type

        response = self.client.get("/files/user/my-files", params=params, headers=headers)
        assert response.status_code == 200, f"Get my files failed: {response.text}"
        return response.json()

    # ========== Project Files (привязка к проекту) ==========

    def attach_file_to_project(
            self: BaseAPIClient,
            project_id: str,
            file_id: str,
            workspace_id: str,
            description: Optional[str] = None,
            tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Привязать существующий файл к проекту
        POST /projects/{project_id}/files/attach
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        data = {
            "file_id": file_id,
            "workspace_id": workspace_id
        }
        if description:
            data["description"] = description
        if tags:
            data["tags"] = tags

        response = self.client.post(
            f"/projects/{project_id}/files/attach",
            json=data,
            headers=headers
        )
        assert response.status_code == 201, f"Attach file to project failed: {response.text}"
        return response.json()

    def list_project_files(
            self: BaseAPIClient,
            project_id: str,
            workspace_id: str,
            limit: int = 100,
            offset: int = 0
    ) -> Dict[str, Any]:
        """Получить список файлов проекта
        GET /projects/{project_id}/files
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {
            "workspace_id": workspace_id,
            "limit": limit,
            "offset": offset
        }
        response = self.client.get(
            f"/projects/{project_id}/files",
            params=params,
            headers=headers
        )
        assert response.status_code == 200, f"List project files failed: {response.text}"
        return response.json()

    def get_project_file(
            self: BaseAPIClient,
            project_id: str,
            file_id: str,
            workspace_id: str
    ) -> Dict[str, Any]:
        """Получить метаданные файла проекта
        GET /projects/{project_id}/files/{file_id}
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {"workspace_id": workspace_id}
        response = self.client.get(
            f"/projects/{project_id}/files/{file_id}",
            params=params,
            headers=headers
        )
        assert response.status_code == 200, f"Get project file failed: {response.text}"
        return response.json()

    def update_project_file_metadata(
            self: BaseAPIClient,
            project_id: str,
            file_id: str,
            workspace_id: str,
            description: Optional[str] = None,
            tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Обновить метаданные файла проекта
        PATCH /projects/{project_id}/files/{file_id}
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {"workspace_id": workspace_id}
        data = {}
        if description is not None:
            data["description"] = description
        if tags is not None:
            data["tags"] = tags

        response = self.client.patch(
            f"/projects/{project_id}/files/{file_id}",
            params=params,
            json=data,
            headers=headers
        )
        assert response.status_code == 200, f"Update project file metadata failed: {response.text}"
        return response.json()

    def detach_file_from_project(
            self: BaseAPIClient,
            project_id: str,
            file_id: str,
            workspace_id: str,
            delete_permanently: bool = False
    ) -> Dict[str, Any]:
        """Отвязать файл от проекта
        DELETE /projects/{project_id}/files/{file_id}
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {
            "workspace_id": workspace_id,
            "delete_permanently": delete_permanently
        }
        response = self.client.delete(
            f"/projects/{project_id}/files/{file_id}",
            params=params,
            headers=headers
        )
        assert response.status_code == 200, f"Detach file from project failed: {response.text}"
        return response.json()

    def get_project_file_download_url(
            self: BaseAPIClient,
            project_id: str,
            file_id: str,
            workspace_id: str,
            expires_in: int = 3600
    ) -> Dict[str, Any]:
        """Получить временную ссылку для скачивания файла проекта
        GET /projects/{project_id}/files/{file_id}/download-url
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        params = {
            "workspace_id": workspace_id,
            "expires_in": expires_in
        }
        response = self.client.get(
            f"/projects/{project_id}/files/{file_id}/download-url",
            params=params,
            headers=headers
        )
        assert response.status_code == 200, f"Get download URL failed: {response.text}"
        return response.json()

    # ========== Project Avatar ==========

    def set_project_avatar(
            self: BaseAPIClient,
            project_id: str,
            file_id: str
    ) -> Dict[str, Any]:
        """Установить аватар проекта
        POST /projects/{project_id}/avatar
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        data = {"file_id": file_id}
        response = self.client.post(
            f"/projects/{project_id}/avatar",
            json=data,
            headers=headers
        )
        assert response.status_code == 201, f"Set project avatar failed: {response.text}"
        return response.json()

    def get_project_avatar(
            self: BaseAPIClient,
            project_id: str
    ) -> Dict[str, Any]:
        """Получить аватар проекта
        GET /projects/{project_id}/avatar
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.get(f"/projects/{project_id}/avatar", headers=headers)
        assert response.status_code == 200, f"Get project avatar failed: {response.text}"
        return response.json()

    def remove_project_avatar(
            self: BaseAPIClient,
            project_id: str
    ) -> Dict[str, Any]:
        """Удалить аватар проекта
        DELETE /projects/{project_id}/avatar
        """
        self.ensure_authenticated()
        headers = self.get_auth_headers()
        response = self.client.delete(f"/projects/{project_id}/avatar", headers=headers)
        assert response.status_code == 200, f"Remove project avatar failed: {response.text}"
        return response.json()

    # ========== Convenience methods ==========

    def upload_and_attach_file_to_project(
            self: BaseAPIClient,
            project_id: str,
            workspace_id: str,
            file_path: str,
            description: Optional[str] = None,
            tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Загрузить файл и сразу привязать к проекту"""
        # 1. Загружаем файл
        upload_result = self.upload_file(
            file_path=file_path,
            file_type="project_file",
            metadata={"description": description} if description else None
        )
        file_id = upload_result["file_id"]

        # 2. Привязываем к проекту
        return self.attach_file_to_project(
            project_id=project_id,
            file_id=file_id,
            workspace_id=workspace_id,
            description=description,
            tags=tags
        )

    def upload_and_set_project_avatar(
            self: BaseAPIClient,
            project_id: str,
            avatar_path: str,
            description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Загрузить аватар и сразу установить для проекта"""
        # 1. Загружаем аватар
        upload_result = self.upload_file(
            file_path=avatar_path,
            file_type="project_avatar",
            metadata={"description": description} if description else None,
            public=True
        )
        file_id = upload_result["file_id"]

        # 2. Устанавливаем как аватар проекта
        return self.set_project_avatar(project_id, file_id)