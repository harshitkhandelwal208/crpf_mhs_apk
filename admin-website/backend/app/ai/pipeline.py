"""
Hierarchical Mental Health & Welfare AI Pipeline
Combines the HK Neural Composite Pipeline architecture with the Mental_Health_Ui
3-tier intent routing, VADER sentiment scoring, RAG clinical skill retrieval,
and dynamic context-aware response generation.
"""

import os
import re
from typing import Any, Dict, List, Optional, Tuple

from app.ai.hk_engine import ContextWindowManager, PipelineContext
from app.ai.knowledge_base import get_knowledge_base

# High-risk crisis patterns from clinical protocols
CRISIS_PATTERNS = [
    r"\b(kill|killing|end)\s+(my)?self\b",
    r"\bsuicid(e|al)\b",
    r"\b(don't|do not|wanna|want to)\s+live\b",
    r"\bend\s+it\s+all\b",
    r"\bno\s+reason\s+to\s+live\b",
    r"\bhurt\s+myself\b",
    r"\btake\s+my\s+(own\s+)?life\b",
    r"\bbetter\s+off\s+dead\b",
    r"\bgive\s+up\s+on\s+life\b",
    r"\bself[- ]?harm\b",
    r"\bcan'?t\s+go\s+on\b",
    r"\bshoot\s+myself\b",
    r"\bwant\s+to\s+die\b",
    r"\bfrag\s+(him|them|myself)\b",
]

# Elevated distress signals
DISTRESS_TERMS = [
    "hopeless", "helpless", "overwhelmed", "burnt out", "burnout",
    "exhausted", "cannot cope", "breaking down", "isolated", "alone",
    "panic", "anxiety", "nightmare", "cannot sleep", "insomnia", "numb"
]

# Positive / Joy signals
JOY_TERMS = [
    "happy", "great", "proud", "good", "relieved", "excited",
    "peaceful", "better", "accomplished", "thankful", "grateful",
    "celebrate", "energy", "optimistic", "glad", "safe"
]


def regex_safety_net(text: str) -> bool:
    """Deterministic crisis safety net."""
    lower = text.lower()
    for pattern in CRISIS_PATTERNS:
        if re.search(pattern, lower):
            return True
    return False


def extract_distress_signals(text: str) -> List[str]:
    """Extract elevated psychological distress keywords."""
    lower = text.lower()
    signals = []
    for term in DISTRESS_TERMS:
        if term in lower:
            signals.append(term.replace(" ", "_"))
    return signals


class MentalHealthPipeline:
    """
    Mental Welfare Hierarchical Pipeline implementation.
    Orchestrates intent routing, micro-lexical VADER sentiment, RAG clinical retrieval,
    trajectory tracking, and empathetic generation.
    """

    def __init__(self):
        self.context_manager = ContextWindowManager(max_context_length=2048, default_strategy="middle_out")
        self.knowledge_base = get_knowledge_base()
        self._vader = None

    def _get_vader(self):
        if self._vader is None:
            try:
                from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
                self._vader = SentimentIntensityAnalyzer()
            except Exception:
                self._vader = False
        return self._vader if self._vader is not False else None

    def analyze_intent_and_morale(self, text: str) -> Tuple[str, int, bool, List[str]]:
        """
        Analyzes user text to compute:
        - mood: 'joy', 'triage', or 'emergency'
        - morale_score: 0-100
        - is_emergency: boolean flag
        - signals: list of detected distress keywords
        """
        is_crisis = regex_safety_net(text)
        signals = extract_distress_signals(text)
        lower = text.lower()

        # 1. Micro Lexical Sentiment (VADER)
        vader = self._get_vader()
        if vader:
            try:
                scores = vader.polarity_scores(text)
                compound = scores.get("compound", 0.0)  # -1.0 to 1.0
                micro_morale = ((compound + 1.0) / 2.0) * 90.0 + 10.0
            except Exception:
                micro_morale = 50.0
        else:
            # Fallback heuristic
            pos_count = sum(1 for term in JOY_TERMS if term in lower)
            neg_count = sum(1 for term in DISTRESS_TERMS if term in lower)
            delta = pos_count - neg_count
            micro_morale = 50.0 + (delta * 12.0)
            micro_morale = max(10.0, min(95.0, micro_morale))

        # 2. Intent Classification & Morale Blending
        if is_crisis:
            mood = "emergency"
            morale_score = 10
        elif signals or micro_morale < 42.0:
            mood = "triage"
            morale_score = int(round(max(15, min(50, micro_morale))))
        elif any(term in lower for term in JOY_TERMS) or micro_morale > 62.0:
            mood = "joy"
            morale_score = int(round(max(65, min(98, micro_morale))))
        else:
            mood = "triage"
            morale_score = int(round(max(40, min(65, micro_morale))))

        return mood, morale_score, is_crisis, signals

    def compute_trajectory(self, recent_scores: List[int]) -> str:
        """Computes longitudinal morale trajectory trend across turns/sessions."""
        if not recent_scores or len(recent_scores) < 2:
            return "STABLE"

        delta = recent_scores[-1] - recent_scores[0]
        recent_avg = sum(recent_scores[-2:]) / 2.0

        if delta <= -20 or recent_scores[-1] < 25:
            return "RAPIDLY DECLINING (Warning)"
        elif delta < -8 or recent_avg < 40:
            return "DECLINING"
        elif delta >= 20 or recent_scores[-1] > 80:
            return "RAPIDLY IMPROVING"
        elif delta > 8 or recent_avg > 65:
            return "IMPROVING"
        else:
            return "STABLE"

    def run(
        self,
        user_input: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        trajectory_trend: Optional[str] = None,
        recent_scores: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Executes the complete mental welfare pipeline for a message turn.
        """
        # Step 1: Intent, Sentiment & Crisis Detection
        mood, morale_score, is_emergency, signals = self.analyze_intent_and_morale(user_input)

        # Step 2: Compute Trajectory
        scores_history = list(recent_scores or [])
        scores_history.append(morale_score)
        trend = trajectory_trend or self.compute_trajectory(scores_history)

        # Step 3: RAG Retrieval from Clinical Knowledge Base
        rag_match = self.knowledge_base.search(user_input, threshold=0.35)
        rag_context = ""
        matched_protocol = None
        if rag_match:
            matched_protocol = rag_match["title"]
            rag_context = f"\n[Relevant Clinical Protocol: {rag_match['title']}]\n{rag_match['content']}\n"

        # Step 4: System Prompt Configuration
        if is_emergency:
            mood_str = "EMERGENCY / CRISIS"
            system_prompt = (
                "You are 'MentalWelfare', an emergency crisis intervention AI for military and armed forces personnel. "
                "A human medical/welfare team has been alerted. Your ONLY job is to provide immediate, gentle, grounding support. "
                "Remind them they are safe, valued, and human help is immediately available. Keep it brief and highly empathetic. "
                "Do not diagnose or give generic advice."
            )
            response_text = (
                "I hear how much pain you are carrying right now, and I want you to know you are not alone in this. "
                "What you are experiencing matters deeply. Please stay safe — an immediate human support option is available "
                "right now through the Get Support button or your unit medical officer. Please connect with someone who can "
                "be beside you through this moment."
            )
        elif mood == "joy":
            mood_str = "JOY / CASUAL"
            system_prompt = (
                "You are 'MentalWelfare', an upbeat, encouraging squadmate assistant for armed forces personnel. "
                "Match the user's positive energy, celebrate their progress with them, and keep responses supportive and concise."
            )
            response_text = (
                f"That is really great to hear! It's rewarding to see positive moments like this on the board. "
                f"Holding onto those wins makes a big difference. How has the rest of your day been shaping up?"
            )
        else:
            mood_str = "STRESS / TRIAGE"
            system_prompt = (
                "You are 'MentalWelfare', a professional, empathetic mental health triage aide for uniformed personnel. "
                "Validate their feelings, provide grounding support, and offer gentle, actionable perspective."
            )
            if rag_match and "sleep" in rag_match["title"].lower():
                response_text = (
                    "Thank you for sharing that with me. Operational shifts and disrupted sleep can take a serious toll on both alertness "
                    "and mood. When your body doesn't get enough recovery, even normal tasks feel heavier. If possible today, try to grab "
                    "a quiet 20-minute rest block, drink some water, and remember you don't have to carry everything at once. What part of your schedule feels heaviest right now?"
                )
            elif rag_match and "family" in rag_match["title"].lower():
                response_text = (
                    "It takes courage to put that into words. Being separated from family during deployments and transfers is one of the "
                    "heaviest aspects of service. It's completely normal to feel that pull. Have you been able to speak with them recently, "
                    "or is there a comrade or welfare representative nearby who knows what you're facing?"
                )
            elif rag_match and "operational" in rag_match["title"].lower():
                response_text = (
                    "Operational stress under sustained tempo is very real, and recognizing it is an important first step. "
                    "Your dedication to the unit is evident, but you also need room to breathe and recharge. Let's take it one step at a time — "
                    "what is one small thing you can take off your plate or get support with today?"
                )
            else:
                response_text = (
                    "Thank you for reaching out and sharing that with me. What you're describing carries real weight, and it's completely "
                    "understandable to feel strained under these conditions. Taking a moment to pause and reflect is a sign of resilience, "
                    "not weakness. Would it help to talk more about what brought this up today?"
                )

        # Step 5: Format Enriched Context for HK Blackboard
        enriched_context = f"""[Real-Time System Context]
Morale Score: {morale_score}/100
Detected Mood: {mood_str}
Session Trajectory: {trend}
Emergency Triggered: {is_emergency}{rag_context}

[User Message]
{user_input}"""

        return {
            "response": response_text,
            "morale_score": morale_score,
            "detected_mood": mood_str,
            "is_emergency": is_emergency,
            "trajectory_trend": trend,
            "matched_protocol": matched_protocol,
            "signals": signals,
            "system_prompt": system_prompt,
            "enriched_context": enriched_context,
        }


# Global singleton pipeline
_pipeline_instance: Optional[MentalHealthPipeline] = None

def get_pipeline() -> MentalHealthPipeline:
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = MentalHealthPipeline()
    return _pipeline_instance
