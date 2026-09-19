"""
HK Neural Framework Pipeline Architecture
Ported and adapted from https://github.com/harshitkhandelwal208/hk
Provides heterogeneous model orchestration (Audio STT, Intent/Token Analysis, LLM Generation),
PipelineContext blackboard state, ContextWindowManager with retention strategies, and PipelineStage.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import math
import re


# ---------------------------------------------------------------------------
# Dynamic Context Window Management (from HK framework)
# ---------------------------------------------------------------------------

class ContextWindowManager:
    """
    Manages sequence length, token budgets, and context retention for single
    and multi-stage inference pipelines. Supports retention strategies:
    - 'middle_out': Preserves head for system prompt/instructions and tail for recent dialogue,
                    dropping intermediate turns when context exceeds budget.
    - 'tail': Keeps the most recent tokens (conversation recency).
    - 'head': Keeps the earliest tokens (system prompt / initial instructions).
    - 'sliding_window': Keeps the final window of tokens.
    """

    def __init__(
        self,
        max_context_length: int = 2048,
        default_strategy: str = "middle_out",
        head_ratio: float = 0.25,
    ):
        self.max_context_length = max_context_length
        self.default_strategy = default_strategy
        self.head_ratio = head_ratio

    def truncate_text(
        self,
        text: str,
        max_chars: Optional[int] = None,
        strategy: Optional[str] = None,
        head_ratio: Optional[float] = None,
    ) -> str:
        """Truncate plain text preserving head/tail structure."""
        limit = max_chars if max_chars is not None else (self.max_context_length * 4)
        if len(text) <= limit:
            return text

        strat = strategy if strategy is not None else self.default_strategy
        ratio = head_ratio if head_ratio is not None else self.head_ratio

        if strat == "tail":
            return text[-limit:]
        elif strat == "head":
            return text[:limit]
        elif strat == "middle_out":
            head_len = max(50, int(limit * ratio))
            tail_len = limit - head_len - 15
            if tail_len <= 0:
                return text[:limit]
            return f"{text[:head_len]}\n[...]\n{text[-tail_len:]}"
        else:
            return text[-limit:]

    def truncate_tokens(
        self,
        tokens: List[Any],
        max_tokens: Optional[int] = None,
        strategy: Optional[str] = None,
        head_ratio: Optional[float] = None,
    ) -> List[Any]:
        """Truncate token sequences using HK retention strategies."""
        limit = max_tokens if max_tokens is not None else self.max_context_length
        total = len(tokens)
        if total <= limit:
            return tokens

        strat = strategy if strategy is not None else self.default_strategy
        ratio = head_ratio if head_ratio is not None else self.head_ratio

        if strat == "tail":
            return tokens[-limit:]
        elif strat == "head":
            return tokens[:limit]
        elif strat == "middle_out":
            head_len = max(1, int(limit * ratio))
            tail_len = limit - head_len
            if tail_len <= 0:
                return tokens[:limit]
            return tokens[:head_len] + tokens[-tail_len:]
        elif strat == "sliding_window":
            return tokens[-limit:]
        else:
            return tokens[-limit:]


# ---------------------------------------------------------------------------
# Universal Pipeline Context Blackboard (from HK framework)
# ---------------------------------------------------------------------------

class PipelineContext(dict):
    """
    Blackboard state dictionary shared across stages in an HK Composite / Universal Pipeline.
    Accumulates raw inputs, intermediate representations, and final stage predictions.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "stages_executed" not in self:
            self["stages_executed"] = []
        if "stage_outputs" not in self:
            self["stage_outputs"] = {}
        if "metadata" not in self:
            self["metadata"] = {}

    def set_output(self, stage_name: str, key: str, value: Any) -> None:
        self[key] = value
        self["stage_outputs"][stage_name] = value
        if stage_name not in self["stages_executed"]:
            self["stages_executed"].append(stage_name)

    def get_latest_text(self) -> Optional[str]:
        """Returns the most recent text representation generated in the context."""
        for key in ["generated_text", "transcription", "text", "prompt"]:
            val = self.get(key)
            if val is not None and isinstance(val, str) and val.strip():
                return val.strip()
        return None


# ---------------------------------------------------------------------------
# Pipeline Stage Abstraction (from HK framework)
# ---------------------------------------------------------------------------

class PipelineStage:
    """
    Universal representation of an executable stage within a multi-modal HK pipeline.
    Can wrap Audio STT, NLP / Intent Analysis, Classification, or Generative LLMs.
    """

    def __init__(
        self,
        name: str,
        stage_fn: Optional[Callable[[PipelineContext, Dict[str, Any]], Any]] = None,
        task_type: str = "generic",
        input_mapping: Optional[Dict[str, str]] = None,
        output_key: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        enabled: bool = True,
    ):
        self.name = name
        self.stage_fn = stage_fn
        self.task_type = task_type
        self.input_mapping = dict(input_mapping or {})
        self.output_key = output_key or name
        self.params = dict(params or {})
        self.enabled = enabled

    def execute(
        self,
        context: PipelineContext,
        params_override: Optional[Dict[str, Any]] = None,
        context_manager: Optional[ContextWindowManager] = None,
    ) -> Any:
        """Executes this individual stage against the pipeline blackboard context."""
        if not self.enabled or self.stage_fn is None:
            return None

        effective_params = dict(self.params)
        if params_override:
            effective_params.update(params_override)

        result = self.stage_fn(context, effective_params)
        context.set_output(self.name, self.output_key, result)
        return result


# ---------------------------------------------------------------------------
# Composite Pipeline (from HK framework)
# ---------------------------------------------------------------------------

class CompositePipeline:
    """
    HK Composite Multi-Model Pipeline (STT -> Intent / Sentiment Analysis -> Generative LLM)
    orchestrated through a unified blackboard context and dynamic context manager.
    """

    def __init__(
        self,
        context_manager: Optional[ContextWindowManager] = None,
        device: str = "cpu",
    ):
        self.context_manager = context_manager or ContextWindowManager()
        self.device = device
        self.stages: Dict[str, PipelineStage] = {}
        self.stage_order: List[str] = []

    def add_stage(self, stage: PipelineStage) -> "CompositePipeline":
        self.stages[stage.name] = stage
        if stage.name not in self.stage_order:
            self.stage_order.append(stage.name)
        return self

    def run(
        self,
        initial_inputs: Optional[Dict[str, Any]] = None,
        context: Optional[PipelineContext] = None,
        stage_params: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> PipelineContext:
        """
        Executes all registered pipeline stages sequentially over the shared blackboard context.
        """
        ctx = context if context is not None else PipelineContext()
        if initial_inputs:
            for k, v in initial_inputs.items():
                ctx[k] = v

        stage_params = stage_params or {}

        for stage_name in self.stage_order:
            stage = self.stages.get(stage_name)
            if stage and stage.enabled:
                override = stage_params.get(stage_name)
                stage.execute(ctx, params_override=override, context_manager=self.context_manager)

        return ctx

