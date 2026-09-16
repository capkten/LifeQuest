from io import BytesIO
import pathlib
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from PIL import Image, UnidentifiedImageError
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.services.user import UserService
from app.api.auth import get_current_user

UPLOAD_DIR = pathlib.Path("uploads/avatars")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
MAX_AVATAR_SIZE = 5 * 1024 * 1024
IMAGE_MIME_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
}
MAX_AVATAR_DIMENSION = 4096
MAX_AVATAR_PIXELS = 16 * 1024 * 1024
MAX_AVATAR_DECODED_PIXELS = 32 * 1024 * 1024
MAX_AVATAR_FRAMES = 32


def detect_image_format(content: bytes):
    """Return a format only after Pillow verifies and decodes the payload."""
    try:
        with Image.open(BytesIO(content)) as image:
            detected_format = (image.format or "").lower()
            if detected_format not in {"png", "jpeg", "gif", "webp"}:
                return None
            if image.width <= 0 or image.height <= 0:
                return None
            if (
                image.width > MAX_AVATAR_DIMENSION
                or image.height > MAX_AVATAR_DIMENSION
                or image.width * image.height > MAX_AVATAR_PIXELS
            ):
                return None
            image.verify()

        # verify() checks the container without decoding pixel data. Reopen the
        # bounded bytes and load every frame so malformed compressed data cannot
        # pass based on a valid header alone.
        with Image.open(BytesIO(content)) as image:
            frame_count = getattr(image, "n_frames", 1)
            if frame_count > MAX_AVATAR_FRAMES:
                return None
            decoded_pixels = 0
            for frame_index in range(frame_count):
                image.seek(frame_index)
                frame_pixels = image.width * image.height
                if (
                    image.width > MAX_AVATAR_DIMENSION
                    or image.height > MAX_AVATAR_DIMENSION
                    or frame_pixels > MAX_AVATAR_PIXELS
                    or decoded_pixels + frame_pixels > MAX_AVATAR_DECODED_PIXELS
                ):
                    return None
                decoded_pixels += frame_pixels
                image.load()
        return detected_format
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        OSError,
        ValueError,
        IndexError,
        EOFError,
    ):
        return None


def _path_exists(path: pathlib.Path) -> bool:
    return path.exists() or path.is_symlink()


def _remove_path(path: pathlib.Path):
    if _path_exists(path):
        path.unlink()


def _restore_avatar_database(db: Session, user_id, previous_avatar):
    statement = update(User).where(User.id == user_id).values(avatar=previous_avatar)
    try:
        db.rollback()
        db.execute(statement)
        db.commit()
    except Exception:
        db.rollback()
        with db.get_bind().begin() as connection:
            connection.execute(statement)


router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserResponse)
def update_current_user(
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = UserService(db)
    try:
        user = service.update_user(current_user, user_in)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    filename = file.filename or ""
    file_ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}")

    upload_size = file.size
    if upload_size is None:
        try:
            position = file.file.tell()
            file.file.seek(0, 2)
            upload_size = file.file.tell()
            file.file.seek(position)
        except (AttributeError, OSError):
            upload_size = None
    if upload_size is not None and upload_size > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=400, detail="File size must be under 5MB")

    content = await file.read(MAX_AVATAR_SIZE)
    if not content or len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=400, detail="File size must be under 5MB")

    detected_format = detect_image_format(content)
    expected_format = "jpeg" if file_ext in {"jpg", "jpeg"} else file_ext
    if detected_format != expected_format:
        raise HTTPException(status_code=400, detail="File content does not match its extension")
    if file.content_type != IMAGE_MIME_TYPES[file_ext]:
        raise HTTPException(status_code=400, detail="File content type does not match its extension")

    # Stage the file separately so validation or database failure cannot touch
    # the current public avatar.
    filename = f"{current_user.id}.{file_ext}"
    file_path = UPLOAD_DIR / filename
    temporary_path = file_path.with_name(f".{file_path.name}.{uuid.uuid4().hex}.tmp")
    backup_path = None
    installed = False
    previous_avatar = current_user.avatar
    avatar_url = f"/uploads/avatars/{filename}"
    try:
        temporary_path.write_bytes(content)

        # UserService owns the existing user update contract and commits the
        # database change before the new public file replaces the old one.
        service = UserService(db)
        service.update_user(current_user, UserUpdate(avatar=avatar_url))

        if _path_exists(file_path):
            backup_path = file_path.with_name(f".{file_path.name}.{uuid.uuid4().hex}.bak")
            file_path.replace(backup_path)
        temporary_path.replace(file_path)
        installed = True
        if backup_path is not None:
            _remove_path(backup_path)
        return {"avatar": avatar_url}
    except Exception:
        try:
            if installed:
                _remove_path(file_path)
            if backup_path is not None and _path_exists(backup_path):
                backup_path.replace(file_path)
            _remove_path(temporary_path)
        finally:
            _restore_avatar_database(db, current_user.id, previous_avatar)
        raise
