"""
Admin File Upload Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from typing import Optional, Tuple
from uuid import UUID
import io
import uuid
from pathlib import Path
from app.database import get_db
from app.schemas.common import ResponseModel
from app.api.admin_deps import require_manager_or_above, get_current_active_admin
from app.utils.admin_activity import log_admin_activity
from app.config import settings
from app.models.admin import Admin
from app.models.category import Category

router = APIRouter()

# Allowed image extensions
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE  # 10MB default

# Category list / app-style icons: square PNG/JPEG/WebP etc., typical store icon range
CATEGORY_ICON_MIN_SIDE = 256
CATEGORY_ICON_MAX_SIDE = 1024


def validate_category_app_icon_image(content: bytes) -> Tuple[int, int]:
    """
    Category images are shown as app-style icons: square, 256–1024 px per side.
    """
    try:
        from PIL import Image
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail="Image validation is not available (Pillow not installed).",
        ) from e
    try:
        with Image.open(io.BytesIO(content)) as im:
            im.verify()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid or corrupted image file.") from e
    try:
        with Image.open(io.BytesIO(content)) as im:
            w, h = im.size
    except Exception as e:
        raise HTTPException(status_code=400, detail="Could not read image dimensions.") from e
    if w != h:
        raise HTTPException(
            status_code=400,
            detail=f"Category image must be square (width and height must match). Got {w}×{h}px.",
        )
    if w < CATEGORY_ICON_MIN_SIDE or w > CATEGORY_ICON_MAX_SIDE:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Category image must be square between {CATEGORY_ICON_MIN_SIDE} and "
                f"{CATEGORY_ICON_MAX_SIDE} pixels per side. Got {w}×{h}px."
            ),
        )
    return w, h


def _extension_from_content_type(content_type: Optional[str]) -> str:
    if not content_type:
        return ""
    c = content_type.lower()
    if "jpeg" in c or "jpg" in c:
        return ".jpg"
    if "png" in c:
        return ".png"
    if "webp" in c:
        return ".webp"
    if "gif" in c:
        return ".gif"
    return ""


def validate_image_file(file: UploadFile) -> tuple[str, str]:
    """Validate and get file extension (mobile clients often omit filename)."""
    file_ext = Path(file.filename).suffix.lower() if file.filename else ""
    if not file_ext:
        file_ext = _extension_from_content_type(file.content_type)
    if file_ext not in ALLOWED_IMAGE_EXTENSIONS:
        file_ext = ".jpg"
    if file_ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}",
        )
    return file_ext, file.filename or "image"


def write_image_upload(
    content: bytes,
    file_ext: str,
    upload_type: str,
    entity_id: Optional[str],
    request: Optional[Request],
) -> str:
    """Write validated image bytes to disk and return public URL."""
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / 1024 / 1024}MB",
        )
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    if entity_id:
        upload_dir = Path(settings.UPLOAD_DIR) / upload_type / entity_id
    else:
        upload_dir = Path(settings.UPLOAD_DIR) / upload_type
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / unique_filename
    with open(file_path, "wb") as f:
        f.write(content)

    if settings.CDN_BASE_URL:
        base_url = settings.CDN_BASE_URL
    elif request:
        base_url = str(request.base_url).rstrip("/")
    else:
        base_url = "http://localhost:8000"

    if entity_id:
        url = f"{base_url}/uploads/{upload_type}/{entity_id}/{unique_filename}"
    else:
        url = f"{base_url}/uploads/{upload_type}/{unique_filename}"
    return url


def save_uploaded_file(file: UploadFile, upload_type: str, entity_id: Optional[UUID] = None, request: Optional[Request] = None) -> str:
    """Save uploaded file and return URL"""
    file_ext, _ = validate_image_file(file)
    content = file.file.read()
    eid = str(entity_id) if entity_id else None
    return write_image_upload(content, file_ext, upload_type, eid, request)


async def save_uploaded_uploadfile(
    file: UploadFile,
    upload_type: str,
    entity_id: Optional[str],
    request: Request,
) -> str:
    """Async variant for multipart routes (reads UploadFile then persists)."""
    file_ext, _ = validate_image_file(file)
    content = await file.read()
    return write_image_upload(content, file_ext, upload_type, entity_id, request)


@router.post("/image", response_model=ResponseModel)
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    upload_type: str = Form(default="general"),
    entity_id: Optional[str] = Form(default=None),
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """
    Upload an image file (multipart form fields: file, upload_type, entity_id).

    upload_type: 'product', 'company', 'brand', 'offer', 'category', 'general'
    entity_id: Optional ID of the entity (required for category/company/brand image DB updates where implemented)
    """
    # Validate upload type
    valid_types = ['product', 'company', 'brand', 'offer', 'category', 'general']
    if upload_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid upload_type. Allowed: {', '.join(valid_types)}"
        )

    eid_clean = entity_id.strip() if entity_id else None

    try:
        file_ext, _ = validate_image_file(file)
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / 1024 / 1024}MB",
            )
        icon_w: Optional[int] = None
        icon_h: Optional[int] = None
        if upload_type == "category":
            icon_w, icon_h = validate_category_app_icon_image(content)
        image_url = write_image_upload(content, file_ext, upload_type, eid_clean, request)
        file_size = len(content)

        if upload_type == "category" and eid_clean:
            cat = db.query(Category).filter(Category.id == eid_clean).first()
            if not cat:
                raise HTTPException(status_code=404, detail="Category not found")
            cat.image = image_url
            db.add(cat)
            db.commit()
            db.refresh(cat)

        entity_uuid: Optional[UUID] = None
        if eid_clean:
            try:
                entity_uuid = UUID(eid_clean)
            except ValueError:
                entity_uuid = None

        response_data = {
            "url": image_url,
            "thumbnailUrl": image_url,
            "size": file_size,
            "width": icon_w,
            "height": icon_h,
        }

        log_admin_activity(
            db=db,
            admin_id=admin.id,
            action="image_uploaded",
            entity_type=upload_type,
            entity_id=entity_uuid,
            details={"filename": file.filename, "url": image_url},
            request=request
        )
        
        return ResponseModel(
            success=True,
            data=response_data,
            message="Image uploaded successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading file: {str(e)}"
        )


@router.post("/images", response_model=ResponseModel)
async def upload_multiple_images(
    request: Request,
    files: list[UploadFile] = File(...),
    upload_type: str = Form(default="general"),
    entity_id: Optional[str] = Form(default=None),
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db)
):
    """Upload multiple image files"""
    if len(files) > 10:  # Limit to 10 files at once
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 files allowed per request"
        )
    
    # Validate upload type
    valid_types = ['product', 'company', 'brand', 'offer', 'category', 'general']
    if upload_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid upload_type. Allowed: {', '.join(valid_types)}"
        )
    
    eid_clean = entity_id.strip() if entity_id else None
    entity_uuid: Optional[UUID] = None
    if eid_clean:
        try:
            entity_uuid = UUID(eid_clean)
        except ValueError:
            entity_uuid = None

    uploaded_files = []

    for file in files:
        try:
            image_url = save_uploaded_file(file, upload_type, entity_uuid, request)
            uploaded_files.append({
                "url": image_url,
                "thumbnailUrl": image_url,
                "filename": file.filename
            })
        except Exception:
            continue

    if not uploaded_files:
        raise HTTPException(
            status_code=400,
            detail="No files were uploaded successfully"
        )

    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action="images_uploaded",
        entity_type=upload_type,
        entity_id=entity_uuid,
        details={"count": len(uploaded_files)},
        request=request
    )
    
    return ResponseModel(
        success=True,
        data={"images": uploaded_files},
        message=f"{len(uploaded_files)} image(s) uploaded successfully"
    )

