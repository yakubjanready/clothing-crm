from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.api.deps import require_permission
from app.core.config import settings
from app.models.user import User

router = APIRouter(prefix="/upload")


class ImageUploadResponse(BaseModel):
    url: str
    filename: str
    content_type: str
    size_bytes: int


def get_media_root() -> Path:
    """FastAPI dependency — testlarda monkey-patch yoki override qilinadi."""
    p = Path(settings.MEDIA_ROOT)
    p.mkdir(parents=True, exist_ok=True)
    return p


_EXT_BY_CT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


@router.post(
    "/image",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_image(
    file: UploadFile = File(...),
    media_root: Path = Depends(get_media_root),
    _: User = Depends(require_permission("product:write")),
) -> ImageUploadResponse:
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Faqat {settings.ALLOWED_IMAGE_TYPES} qabul qilinadi (kelgan: {file.content_type})",
        )

    contents = await file.read()
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Fayl o'lchami {settings.MAX_UPLOAD_MB}MB dan oshmasin",
        )
    if not contents:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Bo'sh fayl")

    ext = _EXT_BY_CT.get(file.content_type, ".bin")
    filename = f"{uuid.uuid4().hex}{ext}"
    target = media_root / filename
    with open(target, "wb") as f:
        f.write(contents)

    url = f"{settings.MEDIA_URL_PREFIX.rstrip('/')}/{filename}"
    return ImageUploadResponse(
        url=url,
        filename=filename,
        content_type=file.content_type,
        size_bytes=len(contents),
    )
