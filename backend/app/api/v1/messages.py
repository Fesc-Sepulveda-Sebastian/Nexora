from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.message import Message, Notification
from app.models.collaboration import CollaborationAgreement
from app.models.user import User
from app.schemas.message import MessageCreate, MessageOut, NotificationOut
from app.schemas.common import APIResponse
from app.core.websocket_manager import ws_manager
from app.api.deps import get_current_user

router = APIRouter(tags=["Mensajería y Notificaciones"])

@router.post("/messages", response_model=APIResponse[MessageOut], status_code=status.HTTP_201_CREATED)
async def send_message(
    msg_in: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    RF-12: Contextual messaging persisted first to PostgreSQL, then emitted via WebSocket.
    """
    collab = db.query(CollaborationAgreement).filter(CollaborationAgreement.id == msg_in.collaboration_id).first()
    if not collab:
        raise HTTPException(status_code=404, detail="Colaboración no encontrada")

    if current_user.id != collab.brand_id and current_user.id != collab.creator_id:
        raise HTTPException(status_code=403, detail="No eres participante de esta colaboración")

    msg = Message(
        collaboration_id=msg_in.collaboration_id,
        sender_id=current_user.id,
        recipient_id=msg_in.recipient_id,
        content=msg_in.content,
        created_at=datetime.utcnow()
    )
    db.add(msg)
    
    # Also add notification for recipient
    notif = Notification(
        user_id=msg_in.recipient_id,
        event_type="new_message",
        title="Nuevo mensaje de colaboración",
        message=f"{current_user.profile.display_name if current_user.profile else 'Usuario'}: {msg_in.content[:40]}...",
        link=f"/collaboration/{collab.id}"
    )
    db.add(notif)
    db.commit()
    db.refresh(msg)

    # Broadcast via WebSocket
    msg_payload = {
        "event": "new_message",
        "data": {
            "id": msg.id,
            "collaboration_id": msg.collaboration_id,
            "sender_id": msg.sender_id,
            "sender_name": current_user.profile.display_name if current_user.profile else "Usuario",
            "content": msg.content,
            "created_at": msg.created_at.isoformat()
        }
    }
    await ws_manager.broadcast_to_room(msg_payload, f"collaboration_{collab.id}")
    await ws_manager.send_personal_message(msg_payload, msg_in.recipient_id)

    return APIResponse(
        success=True,
        message="Mensaje enviado",
        data=MessageOut.model_validate(msg)
    )

@router.get("/messages/{collaboration_id}", response_model=APIResponse[List[MessageOut]])
def get_collaboration_messages(
    collaboration_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    messages = db.query(Message).filter(Message.collaboration_id == collaboration_id).order_by(Message.created_at.asc()).all()
    return APIResponse(
        success=True,
        data=[MessageOut.model_validate(m) for m in messages]
    )

@router.get("/notifications", response_model=APIResponse[List[NotificationOut]])
def get_user_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notifs = db.query(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.created_at.desc()).limit(20).all()
    return APIResponse(
        success=True,
        data=[NotificationOut.model_validate(n) for n in notifs]
    )
