"""
Admin bulk import from Excel (.xlsx): categories, companies, brands, products (no images).
"""
from enum import Enum
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.admin_deps import require_manager_or_above
from app.database import get_db
from app.models.admin import Admin
from app.schemas.common import ResponseModel
from app.services import excel_bulk_import as xbi
from app.utils.admin_activity import log_admin_activity

router = APIRouter()

MAX_IMPORT_BYTES = 5 * 1024 * 1024  # 5 MB


class ImportEntity(str, Enum):
    categories = "categories"
    companies = "companies"
    brands = "brands"
    products = "products"


def _template_bytes(entity: ImportEntity) -> tuple[bytes, str]:
    if entity == ImportEntity.companies:
        headers = ["name", "description"]
        example = ["Sample Company Pvt Ltd", "Wholesale distributor"]
        filename = "company_import_template.xlsx"
    elif entity == ImportEntity.categories:
        headers = [
            "name",
            "description",
            "parent_name",
            "division_slug",
            "display_order",
            "is_active",
            "icon",
            "color",
            "meta_title",
            "meta_description",
        ]
        example = [
            "Bathing Bar",
            "Soaps and bars",
            "",
            "",
            0,
            "true",
            "",
            "#1E6DD8",
            "",
            "",
        ]
        filename = "category_import_template.xlsx"
    elif entity == ImportEntity.brands:
        headers = ["name", "company_name", "category_name"]
        example = ["Dove", "Hindustan Unilever Ltd", "Bathing Bar"]
        filename = "brand_import_template.xlsx"
    else:
        # Required: name, mrp, unit. selling_price optional (defaults to mrp). Optional: names or IDs, etc. No images.
        headers = [
            "name",
            "mrp",
            "selling_price",
            "unit",
            "category_name",
            "brand_name",
            "company_name",
            "category_id",
            "brand_id",
            "company_id",
            "division_slug",
            "stock_quantity",
            "min_order_quantity",
            "pieces_per_set",
            "commission_cost",
            "description",
            "hsn_code",
            "is_featured",
            "is_available",
            "expiry_date",
        ]
        example = [
            "Sample Product 100g",
            100,
            85,
            "piece",
            "Bathing Bar",
            "Dove",
            "Hindustan Unilever Ltd",
            "",
            "",
            "",
            "",
            50,
            1,
            1,
            0,
            "Optional description",
            "34011190",
            "false",
            "true",
            "",
        ]
        filename = "product_import_template.xlsx"

    content = xbi.build_template_workbook("Import", headers, example)
    return content, filename


@router.get("/template/{entity}", summary="Download blank Excel template")
async def download_template(
    entity: ImportEntity,
    admin: Admin = Depends(require_manager_or_above),
):
    content, filename = _template_bytes(entity)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/upload/{entity}", response_model=ResponseModel)
async def upload_import(
    entity: ImportEntity,
    request: Request,
    file: UploadFile = File(...),
    admin: Admin = Depends(require_manager_or_above),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload an .xlsx file",
        )
    raw = await file.read()
    if len(raw) > MAX_IMPORT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large (max {MAX_IMPORT_BYTES // (1024 * 1024)} MB)",
        )

    try:
        _, rows = xbi.parse_excel_rows(raw, import_entity=entity.value)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read Excel file: {e}",
        )

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data rows found (header only or empty sheet)",
        )

    admin_id_str = str(admin.id) if admin.id is not None else None

    if entity == ImportEntity.companies:
        created, errors = xbi.import_companies(db, rows)
    elif entity == ImportEntity.categories:
        created, errors = xbi.import_categories(db, rows)
    elif entity == ImportEntity.brands:
        created, errors = xbi.import_brands(db, rows)
    else:
        created, errors = xbi.import_products(db, rows, admin_id_str)

    log_admin_activity(
        db=db,
        admin_id=admin.id,
        action=f"bulk_import_{entity.value}",
        entity_type=entity.value,
        entity_id=None,
        details={"created": created, "errors_count": len(errors)},
        request=request,
    )

    return ResponseModel(
        success=True,
        data={
            "created": created,
            "failed": len(errors),
            "errors": errors[:50],
            "errors_truncated": len(errors) > 50,
        },
        message=f"Import finished: {created} created, {len(errors)} row(s) failed",
    )
