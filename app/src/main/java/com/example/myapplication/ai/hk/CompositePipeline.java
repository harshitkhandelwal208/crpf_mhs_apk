package com.example.myapplication.ai.hk;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * HK Neural Framework: Composite Multi-Model Pipeline
 * Ported from https://github.com/harshitkhandelwal208/hk
 * Coordinates multi-stage inference execution across blackboard context.
 */
public class CompositePipeline {

    private final ContextWindowManager contextManager;
    private final Map<String, PipelineStage> stages;
    private final List<String> stageOrder;

    public CompositePipeline() {
        this(new ContextWindowManager());
    }

    public CompositePipeline(ContextWindowManager contextManager) {
        this.contextManager = contextManager != null ? contextManager : new ContextWindowManager();
        this.stages = new HashMap<>();
        this.stageOrder = new ArrayList<>();
    }

    public ContextWindowManager getContextManager() {
        return contextManager;
    }

    public CompositePipeline addStage(PipelineStage stage) {
        if (stage == null) return this;
        stages.put(stage.getName(), stage);
        if (!stageOrder.contains(stage.getName())) {
            stageOrder.add(stage.getName());
        }
        return this;
    }

    public PipelineContext run(Map<String, Object> initialInputs, PipelineContext context, Map<String, Map<String, Object>> stageParams) {
        PipelineContext ctx = (context != null) ? context : new PipelineContext();
        if (initialInputs != null) {
            ctx.putAll(initialInputs);
        }

        for (String stageName : stageOrder) {
            PipelineStage stage = stages.get(stageName);
            if (stage != null && stage.isEnabled()) {
                Map<String, Object> override = (stageParams != null) ? stageParams.get(stageName) : null;
                stage.execute(ctx, override, contextManager);
            }
        }

        return ctx;
    }

    public PipelineContext run(Map<String, Object> initialInputs) {
        return run(initialInputs, null, null);
    }
}

