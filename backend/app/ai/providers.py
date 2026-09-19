"""
AI Provider abstraction layer for CRPF MHS Backend
Implements HK Neural Framework provider, OpenAI-compatible provider, and Mock provider.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from app.ai.pipeline import get_pipeline, regex_safety_net, extract_distress_signals
from app.config import settings


@dataclass(frozen=True)
class JournalAnalysis:
    wellbeing_signal: str
    confidence: float
    signals: List[str]
    requires_human_review: bool


class AIProvider(ABC):
    @abstractmethod
    def chat(
        self, message: str, history: List[Dict[str, str]], user_id: Optional[str] = None
    ) -> Tuple[str, bool, Dict[str, Any]]:
        """Returns (response_text, is_emergency, metadata_dict)."""
        pass

    @abstractmethod
    def analyze_journal(self, text: str) -> JournalAnalysis:
        """Analyzes journal text for operational stress and welfare signals."""
        pass

    @abstractmethod
    def transcribe(self, content: bytes, mime_type: str) -> Tuple[str, bool]:
        """Transcribes audio into text; returns (transcript, requires_review)."""
        pass


class HKMentalHealthProvider(AIProvider):
    """
    Primary provider powered by the HK Neural Framework and Mental Welfare Intelligence.
    """

    def __init__(self):
        self.pipeline = get_pipeline()

    def chat(
        self, message: str, history: List[Dict[str, str]], user_id: Optional[str] = None
    ) -> Tuple[str, bool, Dict[str, Any]]:
        res = self.pipeline.run(user_input=message, conversation_history=history)
        meta = {
            "morale_score": res["morale_score"],
            "detected_mood": res["detected_mood"],
            "trajectory_trend": res["trajectory_trend"],
            "matched_protocol": res["matched_protocol"],
            "signals": res["signals"],
        }
        return res["response"], res["is_emergency"], meta

    def analyze_journal(self, text: str) -> JournalAnalysis:
        mood, morale_score, is_crisis, signals = self.pipeline.analyze_intent_and_morale(text)
        if is_crisis:
            return JournalAnalysis("HIGH", 0.95, ["crisis_language_detected"], True)

        if signals or morale_score < 40:
            level = "ELEVATED" if len(signals) >= 2 else "MODERATE"
            confidence = round(0.50 + min(0.40, len(signals) * 0.15), 2)
            return JournalAnalysis(level, confidence, signals, requires_human_review=(level == "ELEVATED"))

        return JournalAnalysis("NORMAL", 0.35, signals, False)

    def transcribe(self, content: bytes, mime_type: str) -> Tuple[str, bool]:
        # Attempt Whisper transcription if whisper is available
        try:
            import tempfile
            import whisper
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
            model = whisper.load_model("base.en").to(device)

            ext = ".wav"
            if "mp4" in mime_type or "m4a" in mime_type: ext = ".m4a"
            elif "ogg" in mime_type: ext = ".ogg"
            elif "mpeg" in mime_type or "mp3" in mime_type: ext = ".mp3"

            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            result = model.transcribe(tmp_path, fp16=torch.cuda.is_available())
            os.unlink(tmp_path)
            transcript = result.get("text", "").strip()
            if transcript:
                return transcript, True
        except Exception:
            pass

        # Fallback review-safe transcription placeholder
        return "Audio note recorded. Please review your thoughts and save your reflection.", True


class MockAIProvider(AIProvider):
    """Deterministic development provider."""

    def chat(
        self, message: str, history: List[Dict[str, str]], user_id: Optional[str] = None
    ) -> Tuple[str, bool, Dict[str, Any]]:
        is_crisis = regex_safety_net(message)
        if is_crisis:
            msg = (
                "I am deeply concerned about what you are sharing. Please stay safe — an immediate human support "
                "option is available through your unit medical officer or the Get Support button. You do not have to carry this alone."
            )
            return msg, True, {"morale_score": 10, "detected_mood": "EMERGENCY", "signals": ["crisis"]}
        return (
            "Thank you for sharing that with me. What you're experiencing is important. How has that been affecting your routine today?",
            False,
            {"morale_score": 50, "detected_mood": "TRIAGE", "signals": []},
        )

    def analyze_journal(self, text: str) -> JournalAnalysis:
        if regex_safety_net(text):
            return JournalAnalysis("HIGH", 0.95, ["potential_high_risk_language"], True)
        signals = extract_distress_signals(text)
        if len(signals) >= 2:
            return JournalAnalysis("ELEVATED", 0.75, signals, True)
        return JournalAnalysis("MODERATE" if signals else "NORMAL", 0.40, signals, False)

    def transcribe(self, content: bytes, mime_type: str) -> Tuple[str, bool]:
        return "Voice entry received and transcribed. Please review before saving.", True


# Global cached provider instance
_provider_instance: Optional[AIProvider] = None

def get_ai_provider() -> AIProvider:
    global _provider_instance
    if _provider_instance is None:
        provider_name = os.getenv("AI_PROVIDER", "hk").lower()
        if provider_name in ("hk", "hk_pipeline", "local"):
            _provider_instance = HKMentalHealthProvider()
        else:
            _provider_instance = MockAIProvider()
    return _provider_instance

