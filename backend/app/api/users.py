import binascii
import pathlib
import struct
import uuid
import zlib
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
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


def _is_valid_png(content: bytes) -> bool:
    if not content.startswith(b"\x89PNG\r\n\x1a\n"):
        return False

    offset = 8
    saw_header = False
    saw_data = False
    saw_palette = False
    saw_iend = False
    width = height = bit_depth = color_type = interlace_method = None
    palette_entries = None
    idat_data = bytearray()
    valid_bit_depths = {
        0: {1, 2, 4, 8, 16},
        2: {8, 16},
        3: {1, 2, 4, 8},
        4: {8, 16},
        6: {8, 16},
    }
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
    while offset < len(content):
        if offset + 12 > len(content):
            return False
        chunk_length = struct.unpack(">I", content[offset:offset + 4])[0]
        chunk_end = offset + 12 + chunk_length
        if chunk_end > len(content):
            return False
        chunk_type = content[offset + 4:offset + 8]
        chunk_data = content[offset + 8:offset + 8 + chunk_length]
        expected_crc = struct.unpack(">I", content[offset + 8 + chunk_length:chunk_end])[0]
        actual_crc = binascii.crc32(chunk_type + chunk_data) & 0xffffffff
        if actual_crc != expected_crc:
            return False
        if chunk_type == b"IHDR":
            if saw_header or chunk_length != 13:
                return False
            width, height, bit_depth, color_type, compression_method, filter_method, interlace_method = struct.unpack(
                ">IIBBBBB", chunk_data
            )
            if (
                width == 0
                or height == 0
                or color_type not in valid_bit_depths
                or bit_depth not in valid_bit_depths[color_type]
                or compression_method != 0
                or filter_method != 0
                or interlace_method not in {0, 1}
            ):
                return False
            saw_header = True
        elif not saw_header:
            return False
        elif chunk_type == b"IDAT":
            idat_data.extend(chunk_data)
            saw_data = True
        elif chunk_type == b"IEND":
            if not saw_data or chunk_length != 0 or chunk_end != len(content):
                return False
            saw_iend = True
            break
        elif chunk_type == b"PLTE":
            if (
                saw_data
                or saw_palette
                or not (3 <= chunk_length <= 768)
                or chunk_length % 3
                or chunk_length // 3 > (1 << bit_depth)
            ):
                return False
            saw_palette = True
            palette_entries = chunk_length // 3
        elif chunk_type[0] & 0x20 == 0:
            # Unknown critical chunks cannot be treated as inert metadata.
            return False
        offset = chunk_end
    if not saw_header or not saw_iend or not idat_data:
        return False
    if color_type == 3 and not saw_palette:
        return False

    row_data_size = (width * channels[color_type] * bit_depth + 7) // 8
    if interlace_method == 0:
        scanline_sizes = [(row_data_size + 1, height, width)]
    else:
        adam7_passes = (
            (0, 0, 8, 8),
            (4, 0, 8, 8),
            (0, 4, 4, 8),
            (2, 0, 4, 4),
            (0, 2, 2, 4),
            (1, 0, 2, 2),
            (0, 1, 1, 2),
        )
        scanline_sizes = []
        for start_x, start_y, step_x, step_y in adam7_passes:
            pass_width = max(0, (width - start_x + step_x - 1) // step_x)
            pass_height = max(0, (height - start_y + step_y - 1) // step_y)
            if pass_width and pass_height:
                pass_row_size = (
                    pass_width * channels[color_type] * bit_depth + 7
                ) // 8
                scanline_sizes.append((pass_row_size + 1, pass_height, pass_width))
    expected_data_size = sum(row_size * rows for row_size, rows, _ in scanline_sizes)
    max_decoded_image_bytes = 64 * 1024 * 1024
    if expected_data_size > max_decoded_image_bytes:
        return False
    try:
        decompressor = zlib.decompressobj()
        decoded = decompressor.decompress(bytes(idat_data), max_decoded_image_bytes + 1)
        decoded += decompressor.flush()
    except zlib.error:
        return False
    if (
        not decompressor.eof
        or decompressor.unused_data
        or decompressor.unconsumed_tail
        or len(decoded) != expected_data_size
    ):
        return False
    offset = 0
    for scanline_size, rows, _ in scanline_sizes:
        for _ in range(rows):
            if decoded[offset] > 4:
                return False
            offset += scanline_size

    if color_type == 3:
        bytes_per_pixel = max(1, (channels[color_type] * bit_depth + 7) // 8)

        def paeth(left, above, upper_left):
            estimate = left + above - upper_left
            left_distance = abs(estimate - left)
            above_distance = abs(estimate - above)
            upper_left_distance = abs(estimate - upper_left)
            if left_distance <= above_distance and left_distance <= upper_left_distance:
                return left
            if above_distance <= upper_left_distance:
                return above
            return upper_left

        offset = 0
        for scanline_size, rows, pixels_per_row in scanline_sizes:
            row_data_length = scanline_size - 1
            previous = bytearray(row_data_length)
            for _ in range(rows):
                filter_type = decoded[offset]
                filtered = decoded[offset + 1:offset + scanline_size]
                current = bytearray(row_data_length)
                for index, value in enumerate(filtered):
                    left = current[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
                    above = previous[index]
                    upper_left = previous[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
                    if filter_type == 0:
                        current[index] = value
                    elif filter_type == 1:
                        current[index] = (value + left) & 0xff
                    elif filter_type == 2:
                        current[index] = (value + above) & 0xff
                    elif filter_type == 3:
                        current[index] = (value + ((left + above) // 2)) & 0xff
                    else:
                        current[index] = (value + paeth(left, above, upper_left)) & 0xff
                if bit_depth == 8:
                    indices = current[:pixels_per_row]
                else:
                    mask = (1 << bit_depth) - 1
                    indices = (
                        (current[index // (8 // bit_depth)]
                         >> (8 - bit_depth * (index % (8 // bit_depth) + 1))) & mask
                        for index in range(pixels_per_row)
                    )
                if any(index >= palette_entries for index in indices):
                    return False
                previous = current
                offset += scanline_size
    return True


def _is_valid_jpeg(content: bytes) -> bool:
    if not content.startswith(b"\xff\xd8") or not content.endswith(b"\xff\xd9"):
        return False

    offset = 2
    saw_frame = False
    saw_scan = False
    frame_markers = {
        *range(0xc0, 0xc4),
        *range(0xc5, 0xc8),
        *range(0xc9, 0xcc),
        *range(0xcd, 0xd0),
    }
    standalone_markers = {0x01, *range(0xd0, 0xd9)}
    while offset < len(content):
        if content[offset] != 0xff:
            return False
        while offset < len(content) and content[offset] == 0xff:
            offset += 1
        if offset >= len(content):
            return False
        marker = content[offset]
        offset += 1
        if marker == 0xd9:
            return saw_frame and saw_scan and offset == len(content)
        if marker == 0x00:
            return False
        if marker in standalone_markers:
            continue
        if offset + 2 > len(content):
            return False
        segment_length = struct.unpack(">H", content[offset:offset + 2])[0]
        if segment_length < 2 or offset + segment_length > len(content):
            return False
        segment_end = offset + segment_length
        if marker in frame_markers:
            if segment_length < 11:
                return False
            height, width = struct.unpack(">HH", content[offset + 3:offset + 7])
            component_count = content[offset + 7]
            if (
                width == 0
                or height == 0
                or content[offset + 2] == 0
                or component_count == 0
                or segment_length != 8 + component_count * 3
            ):
                return False
            saw_frame = True
        if marker == 0xda:
            if not saw_frame or segment_length < 8:
                return False
            saw_scan = True
            saw_scan_data = False
            scan_offset = segment_end
            while scan_offset < len(content):
                if content[scan_offset] != 0xff:
                    saw_scan_data = True
                    scan_offset += 1
                    continue
                if scan_offset + 1 >= len(content):
                    return False
                next_byte = content[scan_offset + 1]
                if next_byte == 0x00 or 0xd0 <= next_byte <= 0xd7:
                    saw_scan_data = True
                    scan_offset += 2
                    continue
                if next_byte == 0xd9:
                    return saw_scan_data and scan_offset + 2 == len(content)
                if next_byte == 0xda:
                    if not saw_scan_data:
                        return False
                    offset = scan_offset
                    break
                if not saw_scan_data:
                    return False
                offset = scan_offset
                break
            else:
                return False
            continue
        offset = segment_end
    return False


def _skip_gif_sub_blocks(content: bytes, offset: int):
    saw_data = False
    while offset < len(content):
        block_size = content[offset]
        offset += 1
        if block_size == 0:
            return offset, saw_data
        offset += block_size
        if offset > len(content):
            return None
        saw_data = saw_data or block_size > 0
    return None


def _is_valid_gif(content: bytes) -> bool:
    if not content.startswith((b"GIF87a", b"GIF89a")) or len(content) < 14:
        return False
    width, height = struct.unpack("<HH", content[6:10])
    if width == 0 or height == 0:
        return False

    offset = 13
    packed = content[10]
    has_global_color_table = bool(packed & 0x80)
    if packed & 0x80:
        offset += 3 * (2 ** ((packed & 0x07) + 1))
    if offset > len(content):
        return False

    saw_image = False
    while offset < len(content):
        block_type = content[offset]
        offset += 1
        if block_type == 0x3b:
            return saw_image and offset == len(content)
        if block_type == 0x2c:
            if offset + 9 > len(content):
                return False
            image_width, image_height = struct.unpack("<HH", content[offset + 4:offset + 8])
            if image_width == 0 or image_height == 0:
                return False
            packed = content[offset + 8]
            left, top = struct.unpack("<HH", content[offset:offset + 4])
            if (
                packed & 0x18
                or left + image_width > width
                or top + image_height > height
            ):
                return False
            offset += 9
            has_local_color_table = bool(packed & 0x80)
            if packed & 0x80:
                offset += 3 * (2 ** ((packed & 0x07) + 1))
                if offset > len(content):
                    return False
            if not has_global_color_table and not has_local_color_table:
                return False
            if offset >= len(content):
                return False
            if not 2 <= content[offset] <= 8:
                return False
            offset += 1
            sub_blocks = _skip_gif_sub_blocks(content, offset)
            if sub_blocks is None or not sub_blocks[1]:
                return False
            offset = sub_blocks[0]
            saw_image = True
            continue
        if block_type == 0x21:
            if offset >= len(content):
                return False
            extension_label = content[offset]
            offset += 1
            if extension_label == 0xf9:
                if offset + 6 > len(content) or content[offset] != 4 or content[offset + 5] != 0:
                    return False
                offset += 6
            elif extension_label == 0x01:
                if offset >= len(content) or content[offset] != 12:
                    return False
                offset += 13
                sub_blocks = _skip_gif_sub_blocks(content, offset)
                if sub_blocks is None:
                    return False
                offset = sub_blocks[0]
            else:
                sub_blocks = _skip_gif_sub_blocks(content, offset)
                if sub_blocks is None:
                    return False
                offset = sub_blocks[0]
            continue
        return False
    return False


def _is_valid_webp(content: bytes) -> bool:
    if not content.startswith(b"RIFF") or len(content) < 12 or content[8:12] != b"WEBP":
        return False
    riff_size = struct.unpack("<I", content[4:8])[0]
    if riff_size != len(content) - 8:
        return False

    def valid_vp8(payload):
        if len(payload) < 10:
            return False
        frame_tag = int.from_bytes(payload[:3], "little")
        if (
            frame_tag & 1
            or not (frame_tag & 0x10)
            or payload[3:6] != b"\x9d\x01\x2a"
        ):
            return False
        width, height = struct.unpack("<HH", payload[6:10])
        if (width & 0x3fff) == 0 or (height & 0x3fff) == 0:
            return False
        first_partition_size = frame_tag >> 5
        return 7 <= first_partition_size <= len(payload) - 10

    def valid_vp8l(payload):
        if len(payload) < 8 or payload[0] != 0x2f:
            return False
        header = int.from_bytes(payload[1:5], "little")
        width = (header & 0x3fff) + 1
        height = ((header >> 14) & 0x3fff) + 1
        version = (header >> 29) & 0x07
        return width > 0 and height > 0 and version == 0 and len(payload) > 5

    def valid_vp8x(payload):
        if len(payload) < 10 or payload[1:4] != b"\x00\x00\x00":
            return False
        width = int.from_bytes(payload[4:7], "little") + 1
        height = int.from_bytes(payload[7:10], "little") + 1
        return width > 0 and height > 0

    offset = 12
    saw_image = False
    saw_extended_header = False
    while offset < len(content):
        if offset + 8 > len(content):
            return False
        chunk_type = content[offset:offset + 4]
        chunk_size = struct.unpack("<I", content[offset + 4:offset + 8])[0]
        chunk_end = offset + 8 + chunk_size
        if chunk_end > len(content):
            return False
        payload = content[offset + 8:chunk_end]
        if chunk_type == b"VP8 ":
            if saw_image or not valid_vp8(payload):
                return False
            saw_image = True
        elif chunk_type == b"VP8L":
            if saw_image or not valid_vp8l(payload):
                return False
            saw_image = True
        elif chunk_type == b"VP8X":
            if saw_extended_header or not valid_vp8x(payload):
                return False
            saw_extended_header = True
        offset = chunk_end + (chunk_size & 1)
        if offset > len(content):
            return False
    return saw_image and offset == len(content)


def detect_image_format(content: bytes):
    if content.startswith(b"\x89PNG") and _is_valid_png(content):
        return "png"
    if content.startswith(b"\xff\xd8") and _is_valid_jpeg(content):
        return "jpeg"
    if content.startswith((b"GIF87a", b"GIF89a")) and _is_valid_gif(content):
        return "gif"
    if content.startswith(b"RIFF") and _is_valid_webp(content):
        return "webp"
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
