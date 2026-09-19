"""
Voice Router - Audio transcription using Whisper STT
"""
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.voice import VoiceEntry
from app.models.audit_log import AuditLog
from app.schemas.schemas import VoiceTranscriptionResponse
from app.ai.providers import get_ai_provider

router = APIRouter(prefix="/voice", tags=["Voice"])


@router.post("/transcribe", response_model=VoiceTranscriptionResponse)
async def transcribe_voice(
    request: Request,
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Transcribes audio file using Whisper STT.
    Returns editable transcript for personnel confirmation before journal submission.
    """
    content = await audio.read(10 * 1024 * 1024)  # 10 MB limit
    if not content:
        raise HTTPException(status_code=400, detail="Empty audio file")

    mime_type = audio.content_type or "audio/wav"
    provider = get_ai_provider()
    transcript, requires_review = provider.transcribe(content, mime_type)

    voice_entry = VoiceEntry(
        user_id=current_user.id,
        mime_type=mime_type,
        transcript=transcript,
        requires_review=requires_review,
    )
    db.add(voice_entry)
    db.flush()

    audit = AuditLog(
        user_id=current_user.id,
        action="VOICE_TRANSCRIBE",
        resource_type="voice_entry",
        resource_id=voice_entry.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(audit)
    db.commit()
    db.refresh(voice_entry)

    return VoiceTranscriptionResponse(
        id=voice_entry.id,
        transcript=voice_entry.transcript,
        requires_review=voice_entry.requires_review,
    )

