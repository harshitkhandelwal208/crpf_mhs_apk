"""
AI Router - AI companion chat and conversation management
"""
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.ai import AIConversation, AIMessage
from app.models.audit_log import AuditLog
from app.schemas.schemas import (
    ChatRequest,
    ChatResponse,
    ChatMessageResponse,
    ConversationResponse,
)
from app.ai.providers import get_ai_provider
from app.services.risk_engine import record_signal

router = APIRouter(prefix="/ai", tags=["AI Companion"])


@router.post("/chat", response_model=ChatResponse)
async def ai_chat(
    body: ChatRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    AI Companion chat turn.
    Evaluates safety, executes RAG clinical retrieval and sentiment analysis,
    persists conversation turns, and escalates to risk engine if crisis is detected.
    """
    # 1. Retrieve or create conversation
    conversation = None
    if body.conversation_id:
        conversation = db.scalar(
            select(AIConversation).where(
                AIConversation.id == body.conversation_id,
                AIConversation.user_id == current_user.id,
            )
        )

    if not conversation:
        conversation = AIConversation(
            user_id=current_user.id,
            title=body.message[:60],
        )
        db.add(conversation)
        db.flush()

    # 2. Retrieve recent message history
    history_messages = db.scalars(
        select(AIMessage)
        .where(AIMessage.conversation_id == conversation.id)
        .order_by(AIMessage.created_at.desc())
        .limit(20)
    ).all()
    history = [
        {"role": m.role, "content": m.content}
        for m in reversed(history_messages)
    ]

    # 3. Persist user message
    user_msg = AIMessage(
        conversation_id=conversation.id,
        role="user",
        content=body.message,
    )
    db.add(user_msg)

    # 4. Invoke AI Engine (HK Composite / Mental Health Pipeline)
    provider = get_ai_provider()
    response_text, is_emergency, metadata = provider.chat(
        body.message, history, user_id=current_user.id
    )

    # 5. Risk escalation & alerting
    if is_emergency:
        signals = metadata.get("signals", []) or ["crisis_language_detected"]
        record_signal(
            db,
            user_id=current_user.id,
            source="ai_chat",
            level="HIGH",
            confidence=0.95,
            signals=signals,
            reason="AI safety net flagged crisis language in companion chat turn",
        )

    # 6. Persist assistant response
    assistant_msg = AIMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=response_text,
        risk_flag=is_emergency,
        morale_score=metadata.get("morale_score"),
        detected_mood=metadata.get("detected_mood"),
        metadata_json=json.dumps(metadata),
    )
    db.add(assistant_msg)

    # 7. Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="AI_CHAT",
        resource_type="ai_conversation",
        resource_id=conversation.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        details=json.dumps({
            "is_emergency": is_emergency,
            "morale_score": metadata.get("morale_score"),
            "mood": metadata.get("detected_mood"),
        }),
    )
    db.add(audit)
    db.commit()
    db.refresh(assistant_msg)

    return ChatResponse(
        conversation_id=conversation.id,
        message=ChatMessageResponse(
            id=assistant_msg.id,
            role=assistant_msg.role,
            content=assistant_msg.content,
            created_at=assistant_msg.created_at,
        ),
        support_escalation=is_emergency,
        morale_score=metadata.get("morale_score"),
        detected_mood=metadata.get("detected_mood"),
        risk_flag=is_emergency,
        safety_message="Confidential human support is available." if is_emergency else None,
    )


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List authenticated user's companion chat conversations."""
    convs = db.scalars(
        select(AIConversation)
        .where(AIConversation.user_id == current_user.id)
        .order_by(AIConversation.updated_at.desc())
    ).all()
    return convs


@router.get("/conversations/{conversation_id}")
async def get_conversation_details(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get conversation turns and metadata."""
    conversation = db.scalar(
        select(AIConversation).where(
            AIConversation.id == conversation_id,
            AIConversation.user_id == current_user.id,
        )
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = db.scalars(
        select(AIMessage)
        .where(AIMessage.conversation_id == conversation.id)
        .order_by(AIMessage.created_at.asc())
    ).all()

    return {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "risk_flag": m.risk_flag,
                "morale_score": m.morale_score,
                "detected_mood": m.detected_mood,
                "created_at": m.created_at,
            }
            for m in messages
        ],
    }

