from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.storage_service import storage_service
from app.api.deps import get_current_user
from app.models.application import DeliverableEvidence
from app.models.user import User, UserRole

router = APIRouter(prefix="/storage", tags=["Almacenamiento de Archivos S3/MinIO"])


class PresignedUrlRequest(BaseModel):
    filename: str = Field(..., min_length=3)
    content_type: str = Field(default="image/jpeg")


@router.post("/presigned-url")
def get_presigned_upload_url(
    req: PresignedUrlRequest,
    current_user: User = Depends(get_current_user),
):
    """
    RF-14: Issues short-lived presigned upload URL for deliverable evidence.
    Validates allowed MIME types before issuing URL.
    """
    try:
        result = storage_service.generate_presigned_upload_url(
            filename=req.filename,
            content_type=req.content_type,
            expires_in=900,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return {
        "success": True,
        "data": result,
    }


@router.put("/upload")
async def upload_local_signed_object(
    request: Request,
    file_key: str = Query(...),
    content_type: str = Query(...),
    expires: int = Query(...),
    sig: str = Query(...),
):
    """
    Signed PUT upload endpoint for local/dev storage mode when MinIO is not attached.
    Validates HMAC signature, expiration, MIME type, and file size (<= 10 MB).
    """
    if not storage_service.verify_local_upload_signature(
        file_key=file_key,
        content_type=content_type,
        expires=expires,
        signature=sig,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="URL de subida firmada inválida o expirada.",
        )

    body = await request.body()
    try:
        meta = storage_service.save_local_object(
            file_key=file_key,
            content_type=content_type,
            data=body,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return {
        "success": True,
        "data": meta,
    }


@router.get("/objects/{file_key:path}")
def download_local_object(
    file_key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    evidence = (
        db.query(DeliverableEvidence)
        .filter(DeliverableEvidence.file_url.contains(file_key))
        .first()
    )
    if evidence and evidence.application:
        app_row = evidence.application
        campaign = app_row.campaign
        is_allowed = (
            current_user.id == app_row.creator_id
            or (campaign and current_user.id == campaign.brand_id)
            or current_user.role == UserRole.ADMINISTRADOR.value
        )
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No autorizado para acceder a esta evidencia.",
            )

    try:
        data, content_type = storage_service.get_local_object(file_key)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return Response(content=data, media_type=content_type)
