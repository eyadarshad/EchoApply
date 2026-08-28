import logging
from typing import List, Optional
from fastapi import APIRouter, Request, Depends, HTTPException, status
from pydantic import BaseModel
from app.limiter import limiter
from app.auth import get_current_user, AuthenticatedUser
from app.sanitize import sanitize_text_input
from app.services.llm_client import llm_client_general as llm_client
from app.services.llm_prompts import CHATBOT_SYSTEM

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    context: Optional[str] = None  # Optional resume/job context

class ChatResponse(BaseModel):
    reply: str

@router.post("/api/chat/message", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat_message(request: Request, payload: ChatRequest, user: AuthenticatedUser = Depends(get_current_user)):
    """Send a message to the AI career chatbot."""
    cleaned_msg = sanitize_text_input(payload.message, max_length=2000, field_name="chat_message", raise_on_injection=True)
    if not cleaned_msg.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message cannot be empty.")
    
    # Build conversation prompt
    prompt_parts = []
    if payload.context:
        prompt_parts.append(f"Candidate Context:\n{payload.context[:3000]}\n")
    for msg in payload.history[-10:]:  # Keep last 10 messages for context window
        prompt_parts.append(f"{msg.role.capitalize()}: {msg.content}")
    prompt_parts.append(f"User: {cleaned_msg}")
    prompt_parts.append("Assistant:")
    
    full_prompt = "\n\n".join(prompt_parts)
    
    import asyncio
    reply = await asyncio.to_thread(
        llm_client.generate_text,
        full_prompt,
        "flash",
        CHATBOT_SYSTEM,
    )
    
    if not reply or not reply.strip():
        reply = "I'm having trouble processing your request right now. Please try again in a moment."
    
    return ChatResponse(reply=reply.strip())
