package com.example.myapplication.ai.hk;

import java.util.HashMap;
import java.util.Map;

/**
 * HK Neural Framework: Pipeline Stage Abstraction
 * Ported from https://github.com/harshitkhandelwal208/hk
 * Encapsulates an executable stage in the multi-modal neural pipeline.
 */
public abstract class PipelineStage {

    private final String name;
    private final String taskType;
    private final String outputKey;
    private final Map<String, Object> params;
    private boolean enabled;

    public PipelineStage(String name, String taskType, String outputKey) {
        this.name = name;
        this.taskType = taskType;
        this.outputKey = outputKey != null ? outputKey : name;
        this.params = new HashMap<>();
        this.enabled = true;
    }

    public String getName() {
        return name;
    }

    public String getTaskType() {
        return taskType;
    }

    public String getOutputKey() {
        return outputKey;
    }

    public Map<String, Object> getParams() {
        return params;
    }

    public boolean isEnabled() {
        return enabled;
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    public abstract Object execute(PipelineContext context, Map<String, Object> paramsOverride, ContextWindowManager contextManager);
}

