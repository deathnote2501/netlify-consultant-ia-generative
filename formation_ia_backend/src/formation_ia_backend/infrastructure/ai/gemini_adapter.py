import google.generativeai as genai
from typing import List, Dict, Any
import json # For converting slide_content_json if it's a dict/object

from formation_ia_backend.core.config import settings

class GeminiAdapter:
    def __init__(self):
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
            # Consider not raising an error if the key isn't set,
            # but rather log a warning and disable AI features,
            # or let it fail only when get_chat_response is called.
            # For now, strict check on init as per original thought.
            raise ValueError("GEMINI_API_KEY is not set or is a placeholder in environment variables.")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        # Model selection can be made configurable if needed
        self.model = genai.GenerativeModel('gemini-pro')

    async def get_chat_response(
        self,
        system_prompt: str, # Overall instructions for the AI's persona and task
        user_message: str,  # The latest message from the user
        slide_content_json: str, # JSON string representing the current slide's content for context
        history: List[Dict[str, str]] # Chat history: List of {"role": "user/ai", "content": "message"}
    ) -> str:
        try:
            # Convert history from {"role": "user/ai", "content": message}
            # to Gemini's format: List[{"role": "user/model", "parts": [{"text": message}]}]
            gemini_history = []
            for msg in history:
                # Ensure 'role' and 'content' keys exist, provide defaults if not.
                role = msg.get("role", "user") # Default to user if role is missing
                content = msg.get("content", "") # Default to empty string if content is missing

                gemini_role = "user" if role == "user" else "model"
                gemini_history.append({"role": gemini_role, "parts": [{"text": content}]})

            # Contextualize the user's current message with the system prompt and slide content.
            # This combined message will be the latest "user" turn sent to Gemini.
            # Ensure slide_content_json is a string. If it's a dict/object, json.dumps it.
            if not isinstance(slide_content_json, str):
                slide_content_str = json.dumps(slide_content_json) # Convert dict to JSON string
            else:
                slide_content_str = slide_content_json

            # Construct the prompt for the current turn:
            # System prompt provides overall guidance.
            # Slide content provides specific context for the current interaction.
            # User message is the user's direct query or input.
            # This approach is simpler than trying to inject a "system" role message into gemini-pro history.
            contextual_user_message_parts = []
            if system_prompt:
                contextual_user_message_parts.append(f"System Instructions: {system_prompt}")

            contextual_user_message_parts.append(f"Current Slide Context: {slide_content_str}")
            contextual_user_message_parts.append(f"User's Message: {user_message}")

            final_user_prompt_for_gemini = "\n\n".join(contextual_user_message_parts)

            # Start a chat session with the existing history
            chat_session = self.model.start_chat(history=gemini_history)

            # Send the new, contextualized user message
            response = await chat_session.send_message_async(final_user_prompt_for_gemini)

            ai_response_text = ""
            if response.parts:
                ai_response_text = "".join(part.text for part in response.parts if hasattr(part, 'text'))
            elif hasattr(response, 'text') and response.text is not None: # Fallback for simpler text responses
                ai_response_text = response.text

            if not ai_response_text:
                # Check for blocking/safety feedback if response is empty
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    block_reason_message = response.prompt_feedback.block_reason_message if response.prompt_feedback.block_reason_message else "Content blocked by safety settings."
                    raise Exception(f"Gemini API call failed: {block_reason_message}")
                # This might also happen if the model genuinely has nothing to say or if there's an issue.
                # Consider logging `response` object for more details.
                # For now, let's assume an empty text means an issue if not blocked.
                # raise Exception("Gemini API returned an empty response text and was not explicitly blocked.")
                # Or, could return a default message like "I'm not sure how to respond to that."
                print("Warning: Gemini API returned an empty response text. Check for potential issues or if this is expected.")


            return ai_response_text

        except Exception as e:
            print(f"Error in GeminiAdapter get_chat_response: {e}")
            # Depending on the desired behavior, either re-raise or return a user-friendly error message
            # For a chatbot, returning a message is often preferred over crashing.
            return "I'm sorry, but I encountered an error trying to process your request with the AI. Please try again later."
