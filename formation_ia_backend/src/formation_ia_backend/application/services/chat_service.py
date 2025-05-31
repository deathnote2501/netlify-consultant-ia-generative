from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
# from sqlalchemy.orm import selectinload # Not used in this version
import json
from typing import List # For List type hint

from formation_ia_backend.domain.models.chat_message import DbChatMessage
from formation_ia_backend.domain.models.slide import DbSlide
from formation_ia_backend.domain.schemas.user import UserRead
from formation_ia_backend.domain.schemas.chat_message import ChatMessageCreate, ChatMessage as ChatMessageSchema
from formation_ia_backend.infrastructure.ai.gemini_adapter import GeminiAdapter
# from formation_ia_backend.core.config import settings # Not directly used here, but could be for global prompts

class ChatService:
    def __init__(self):
        # Initialize GeminiAdapter.
        # This might raise ValueError if GEMINI_API_KEY is not set, effectively disabling the service.
        try:
            self.gemini_adapter = GeminiAdapter()
        except ValueError as e:
            print(f"Error initializing GeminiAdapter in ChatService: {e}")
            # Optionally, set self.gemini_adapter to None and handle this in process_user_message
            # For now, let it raise, or the calling code should handle this service not being available.
            raise  # Re-raise the exception to make it clear service cannot function

    async def process_user_message(
        self,
        db: AsyncSession,
        current_user: UserRead,
        slide_id: int,
        user_message_str: str # Renamed from user_message to avoid confusion with ChatMessage model
    ) -> str: # Returns AI response as string

        # 1. Retrieve the current slide
        slide_result = await db.execute(select(DbSlide).filter(DbSlide.id == slide_id))
        slide = slide_result.scalars().first()
        if not slide:
            # This error should ideally be caught at the API layer to return a proper HTTP response.
            raise ValueError(f"Slide with id {slide_id} not found.")

        # 2. Retrieve last 10 chat messages for the user and slide
        history_result = await db.execute(
            select(DbChatMessage)
            .filter(DbChatMessage.user_id == current_user.id, DbChatMessage.slide_id == slide_id)
            .order_by(DbChatMessage.timestamp.desc())
            .limit(10)
        )
        db_chat_history = list(reversed(history_result.scalars().all())) # Oldest to newest for AI history

        # 3. Format history for GeminiAdapter
        formatted_history = []
        for msg in db_chat_history:
            # GeminiAdapter expects role "user" or "ai" (or "model"). DbChatMessage.role should align.
            formatted_history.append({"role": msg.role, "content": msg.content})

        # 4. Construct system_prompt (global + slide-specific)
        global_system_prompt = "You are an AI assistant for an online course. Be helpful, concise, and stay on topic with the slide's content."
        full_system_prompt = global_system_prompt
        if slide.specific_prompt:
            full_system_prompt += f" Specific instructions for this slide: {slide.specific_prompt}"

        # Convert slide.content (dict) to JSON string for GeminiAdapter
        slide_content_json_str = json.dumps(slide.content)

        # 5. Call GeminiAdapter.get_chat_response
        ai_response_str = await self.gemini_adapter.get_chat_response(
            system_prompt=full_system_prompt,
            user_message=user_message_str,
            slide_content_json=slide_content_json_str,
            history=formatted_history
        )

        # 6. Store user message and AI response in DbChatMessage
        user_chat_message = DbChatMessage(
            user_id=current_user.id,
            slide_id=slide_id,
            role="user", # User's message
            content=user_message_str
            # timestamp is server_default in DbChatMessage model
        )
        db.add(user_chat_message)

        ai_chat_message = DbChatMessage(
            user_id=current_user.id, # AI response is part of the user's session with this slide
            slide_id=slide_id,
            role="ai", # AI's response (GeminiAdapter returns "model", but we store as "ai")
                      # Ensure consistency or map "model" to "ai" if needed.
                      # For now, assuming GeminiAdapter provides a string we can store.
            content=ai_response_str
        )
        db.add(ai_chat_message)

        try:
            await db.commit()
            await db.refresh(user_chat_message) # To get timestamp if needed later, though not strictly necessary here
            await db.refresh(ai_chat_message)
        except Exception as e:
            await db.rollback()
            print(f"Error committing chat messages: {e}")
            # Decide how to handle this error. The AI response is generated,
            # but saving failed. Could return AI response anyway with a warning,
            # or raise an error indicating save failure.
            raise Exception(f"Failed to save chat messages: {str(e)}") from e


        # 7. Return AI response
        return ai_response_str

    async def get_chat_history_for_slide(
        self,
        db: AsyncSession,
        current_user: UserRead,
        slide_id: int,
        limit: int = 100
    ) -> List[ChatMessageSchema]: # Corrected List type hint
        """Retrieves chat history for a given user and slide."""
        result = await db.execute(
            select(DbChatMessage)
            .filter(DbChatMessage.user_id == current_user.id, DbChatMessage.slide_id == slide_id)
            .order_by(DbChatMessage.timestamp.asc()) # Oldest first for display
            .limit(limit)
        )
        messages = result.scalars().all()
        return [ChatMessageSchema.model_validate(msg) for msg in messages]
