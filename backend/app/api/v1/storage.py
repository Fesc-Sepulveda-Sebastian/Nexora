from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from app.services.storage_service import storage_service
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/storage", tags=["Almacenamiento de Archivos S3/MinIO"])

class PresignedUrlRequest(BaseModel):
    filename: str = Field(..., min_length=3)
    content_type: str = Field(default="image/jpeg")

@router.post("/presigned-url")
def get_presigned_upload_url(
    req: PresignedUrlRequest,
    current_user: User = Depends(get_current_user)
):
    """
    RF-14: Issues short-lived presigned upload URL for deliverable evidence.
    Max size 10 MB, minimum 0.2 MB.
    """
    result = storage_service.generate_presigned_upload_url(
        filename=req.filename,
        content_type=req.content_type,
        expires_in=900
    )
    return {
        "success": True,
        "data": result
    }
