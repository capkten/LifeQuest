import pathlib
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
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


def detect_image_format(content: bytes):
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        if (
            len(content) >= 33
            and content[8:12] == b"\x00\x00\x00\x0d"
            and content[12:16] == b"IHDR"
        ):
            return "png"
        return None
    if content.startswith(b"\xff\xd8\xff"):
        return "jpeg" if content.endswith(b"\xff\xd9") else None
    if content.startswith((b"GIF87a", b"GIF89a")):
        return "gif" if len(content) >= 13 else None
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "webp" if len(content) >= 20 else None
    return None

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
    # Validate extension
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

    # Generate unique filename
    filename = f"{current_user.id}.{file_ext}"
    file_path = UPLOAD_DIR / filename

    # Save file
    with open(file_path, "wb") as buffer:
        buffer.write(content)

    # Update user avatar URL
    service = UserService(db)
    avatar_url = f"/uploads/avatars/{filename}"
    service.update_user(current_user, UserUpdate(avatar=avatar_url))

    return {"avatar": avatar_url}
