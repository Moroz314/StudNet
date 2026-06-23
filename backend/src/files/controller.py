from fastapi import APIRouter, Depends, HTTPException, UploadFile, File as FastAPIFile, Form, status
from typing import List, Optional
from uuid import UUID
import json
from ..users.auth.service.utils import verify_token
from .service import get_file_service, FileService
from .schemas import (
    FileType, FileUploadResponse, MultipleFilesUploadResponse,
    FileInfoResponse, FileDeleteResponse
)

files_router = APIRouter(prefix="/files", tags=["Files"])


@files_router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
        file: UploadFile = FastAPIFile(...),
        file_type: FileType = Form(...),
        metadata: Optional[str] = Form(None),
        public: bool = Form(False),
        user_id: int = Depends(verify_token),
        file_service: FileService = Depends(get_file_service)
):
    """
    Загрузка одного файла

    - **file**: Загружаемый файл
    - **file_type**: Тип файла (avatar, project_file, и т.д.)
    - **metadata**: Дополнительная метаинформация в формате JSON
    - **public**: Сделать файл публичным
    """
    metadata_dict = None
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid metadata JSON")

    result = await file_service.upload_file(
        file=file,
        file_type=file_type,
        user_id=user_id,
        metadata=metadata_dict,
        public=public
    )

    return result


@files_router.post("/upload-multiple", response_model=MultipleFilesUploadResponse)
async def upload_multiple_files(
        files: List[UploadFile] = FastAPIFile(...),
        file_type: FileType = Form(...),
        metadata: Optional[str] = Form(None),
        public: bool = Form(False),
        user_id: int = Depends(verify_token),
        file_service: FileService = Depends(get_file_service)
):
    """
    Загрузка нескольких файлов
    """
    metadata_dict = None
    if metadata:
        import json
        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid metadata JSON")

    result = await file_service.upload_multiple_files(
        files=files,
        file_type=file_type,
        user_id=user_id,
        metadata=metadata_dict,
        public=public
    )

    return result


@files_router.get("/{file_id}", response_model=FileInfoResponse)
async def get_file_info(
        file_id: UUID,
        user_id: int = Depends(verify_token),
        file_service: FileService = Depends(get_file_service)
):
    """
    Получение информации о файле
    """
    result = await file_service.get_file_info(
        file_id=file_id,
        user_id=user_id
    )

    return result


@files_router.delete("/{file_id}", response_model=FileDeleteResponse)
async def delete_file(
        file_id: UUID,
        user_id: int = Depends(verify_token),
        file_service: FileService = Depends(get_file_service)
):
    """
    Удаление файла (только для владельца)
    """
    result = await file_service.delete_file(
        file_id=file_id,
        user_id=user_id
    )

    return FileDeleteResponse(**result)


@files_router.get("/{file_id}/url")
async def get_file_url(
        file_id: UUID,
        expires_in: int = 3600,
        user_id: int = Depends(verify_token),
        file_service: FileService = Depends(get_file_service)
):
    """
    Получение URL для доступа к файлу
    """
    url = await file_service.get_file_url(
        file_id=file_id,
        user_id=user_id,
        expires_in=expires_in
    )

    return {"url": url, "expires_in": expires_in}


@files_router.get("/user/my-files", response_model=List[FileInfoResponse])
async def get_my_files(
        file_type: Optional[FileType] = None,
        limit: int = 100,
        user_id: int = Depends(verify_token),
        file_service: FileService = Depends(get_file_service)
):
    """
    Получение всех файлов текущего пользователя
    """
    result = await file_service.get_user_files(
        user_id=user_id,
        file_type=file_type,
        limit=limit
    )

    return result