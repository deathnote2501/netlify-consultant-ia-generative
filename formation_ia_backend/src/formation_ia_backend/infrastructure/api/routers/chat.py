from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select # Required for the workaround in POST /
from typing import List

from pydantic import BaseModel # Import BaseModel for ChatRequest

from formation_ia_backend.infrastructure.database.session import get_async_db
from formation_ia_backend.application.services.chat_service import ChatService
from formation_ia_backend.application.services.user_service import current_active_verified_user
from formation_ia_backend.domain.schemas.user import UserRead
from formation_ia_backend.domain.schemas.chat_message import ChatMessage as ChatMessageSchema
from formation_ia_backend.domain.models.chat_message import DbChatMessage # Required for the workaround in POST /

# Define a Pydantic model for the request body of the chat endpoint
class ChatRequest(BaseModel):
    slide_id: int
    message: str

router = APIRouter()

# Dependency to get ChatService instance
def get_chat_service() -> ChatService:
    try:
        return ChatService()
    except ValueError as e: # Catch Gemini API key error from ChatService.__init__
        # This makes the chat functionality unavailable if AI service isn't configured
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Chat service is unavailable: {str(e)}"
        )

@router.post(
    "/",
    response_model=ChatMessageSchema,
    dependencies=[Depends(current_active_verified_user)]
)
async def send_chat_message(
    chat_request: ChatRequest = Body(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: UserRead = Depends(current_active_verified_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    try:
        # Assuming process_user_message saves user & AI messages and returns AI's content string
        _ = await chat_service.process_user_message(
            db=db,
            current_user=current_user,
            slide_id=chat_request.slide_id,
            user_message_str=chat_request.message
        )

        # Workaround: Fetch the last saved AI message for this user/slide to return the full ChatMessageSchema.
        # This is fragile and ideally, process_user_message would return the saved AI message object/schema.
        result = await db.execute(
            select(DbChatMessage)
            .filter(
                DbChatMessage.user_id == current_user.id,
                DbChatMessage.slide_id == chat_request.slide_id,
                DbChatMessage.role == "ai" # Ensure we fetch the AI's response
            )
            .order_by(DbChatMessage.timestamp.desc())
            .limit(1)
        )
        ai_db_message = result.scalars().first()

        if not ai_db_message:
            # This case should ideally not be reached if process_user_message guarantees saving.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI message was generated but could not be retrieved."
            )
        return ChatMessageSchema.model_validate(ai_db_message)

    except ValueError as ve:
        # Catch specific ValueErrors from service layer (e.g., slide not found)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except HTTPException as he:
        # Re-raise HTTPExceptions (like from get_chat_service or auth)
        raise he
    except Exception as e:
        print(f"Unexpected error in POST /chat endpoint: {e}") # Log for server visibility
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred in the chat."
        )

@router.get(
    "/history/{slide_id}",
    response_model=List[ChatMessageSchema],
    dependencies=[Depends(current_active_verified_user)]
)
async def get_history(
    slide_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserRead = Depends(current_active_verified_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    try:
        return await chat_service.get_chat_history_for_slide(
            db=db,
            current_user=current_user,
            slide_id=slide_id
        )
    except ValueError as ve: # Example: if service raised ValueError for some reason
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Unexpected error in GET /chat/history/{slide_id} endpoint: {e}") # Log for server visibility
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat history."
        )
