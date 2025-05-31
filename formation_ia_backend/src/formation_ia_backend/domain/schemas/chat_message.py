import uuid
from datetime import datetime
from pydantic import BaseModel

class ChatMessageBase(BaseModel):
    role: str
    content: str

class ChatMessageCreate(ChatMessageBase):
    slide_id: int # Received from client when they send a message

class ChatMessage(ChatMessageBase): # Schema for reading/returning messages
    id: uuid.UUID
    user_id: uuid.UUID # To associate message with user
    slide_id: int
    timestamp: datetime

    model_config = {
        "from_attributes": True # Pydantic V2
    }
