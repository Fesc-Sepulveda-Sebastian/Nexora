from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class MessageCreate(BaseModel):
    collaboration_id: str
    recipient_id: str
    content: str = Field(..., min_length=1, max_length=2000)

class MessageOut(BaseModel):
    id: str
    collaboration_id: str
    sender_id: str
    recipient_id: str
    content: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

class NotificationOut(BaseModel):
    id: str
    user_id: str
    event_type: str
    title: str
    message: str
    link: Optional[str] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True
