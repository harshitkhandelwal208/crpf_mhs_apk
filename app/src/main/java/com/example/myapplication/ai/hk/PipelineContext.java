package com.example.myapplication.ai.hk;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * HK Neural Framework: Universal Pipeline Context Blackboard
 * Ported from https://github.com/harshitkhandelwal208/hk
 * Shared state container carrying multi-modal stage inputs, intermediate representations,
 * and final inference outputs.
 */
public class PipelineContext extends HashMap<String, Object> {

    public PipelineContext() {
        super();
        put("stages_executed", new ArrayList<String>());
        put("stage_outputs", new HashMap<String, Object>());
        put("metadata", new HashMap<String, Object>());
    }

    @SuppressWarnings("unchecked")
    public List<String> getStagesExecuted() {
        return (List<String>) get("stages_executed");
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> getStageOutputs() {
        return (Map<String, Object>) get("stage_outputs");
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> getMetadata() {
        return (Map<String, Object>) get("metadata");
    }

    public void setOutput(String stageName, String key, Object value) {
        put(key, value);
        getStageOutputs().put(stageName, value);
        List<String> executed = getStagesExecuted();
        if (!executed.contains(stageName)) {
            executed.add(stageName);
        }
    }

    public String getLatestText() {
        String[] keys = {"generated_text", "transcription", "text", "prompt", "user_input"};
        for (String k : keys) {
            Object val = get(k);
            if (val instanceof String) {
                String str = ((String) val).trim();
                if (!str.isEmpty()) {
                    return str;
                }
            }
        }
        return null;
    }

    public boolean getBoolean(String key, boolean defaultVal) {
        Object v = get(key);
        return v instanceof Boolean ? (Boolean) v : defaultVal;
    }

    public int getInt(String key, int defaultVal) {
        Object v = get(key);
        return v instanceof Number ? ((Number) v).intValue() : defaultVal;
    }

    public String getString(String key, String defaultVal) {
        Object v = get(key);
        return v instanceof String ? (String) v : defaultVal;
    }
}
