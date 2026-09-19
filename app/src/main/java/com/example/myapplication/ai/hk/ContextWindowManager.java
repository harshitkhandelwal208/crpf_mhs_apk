package com.example.myapplication.ai.hk;

import java.util.ArrayList;
import java.util.List;

/**
 * HK Neural Framework: Dynamic Context Window Manager
 * Ported from https://github.com/harshitkhandelwal208/hk
 * Manages token budgets, sequence boundaries, and retention strategies for on-device inference.
 */
public class ContextWindowManager {

    public static final String STRATEGY_MIDDLE_OUT = "middle_out";
    public static final String STRATEGY_TAIL = "tail";
    public static final String STRATEGY_HEAD = "head";
    public static final String STRATEGY_SLIDING_WINDOW = "sliding_window";

    private final int maxContextLength;
    private final String defaultStrategy;
    private final float headRatio;

    public ContextWindowManager() {
        this(2048, STRATEGY_MIDDLE_OUT, 0.25f);
    }

    public ContextWindowManager(int maxContextLength, String defaultStrategy, float headRatio) {
        this.maxContextLength = maxContextLength;
        this.defaultStrategy = defaultStrategy;
        this.headRatio = headRatio;
    }

    public int getMaxContextLength() {
        return maxContextLength;
    }

    public String getDefaultStrategy() {
        return defaultStrategy;
    }

    public float getHeadRatio() {
        return headRatio;
    }

    /**
     * Truncates plain text preserving head/tail structure according to active retention strategy.
     */
    public String truncateText(String text, Integer maxChars, String strategy, Float customHeadRatio) {
        if (text == null) return "";
        int limit = (maxChars != null) ? maxChars : (this.maxContextLength * 4);
        if (text.length() <= limit) {
            return text;
        }

        String strat = (strategy != null) ? strategy : this.defaultStrategy;
        float ratio = (customHeadRatio != null) ? customHeadRatio : this.headRatio;

        if (STRATEGY_TAIL.equals(strat)) {
            return text.substring(text.length() - limit);
        } else if (STRATEGY_HEAD.equals(strat)) {
            return text.substring(0, limit);
        } else if (STRATEGY_MIDDLE_OUT.equals(strat)) {
            int headLen = Math.max(50, (int) (limit * ratio));
            int tailLen = limit - headLen - 15;
            if (tailLen <= 0 || (headLen + tailLen) >= text.length()) {
                return text.substring(0, Math.min(limit, text.length()));
            }
            return text.substring(0, headLen) + "\n[...]\n" + text.substring(text.length() - tailLen);
        } else {
            return text.substring(text.length() - limit);
        }
    }

    /**
     * Truncates token sequences using HK retention strategies.
     */
    public <T> List<T> truncateTokens(List<T> tokens, Integer maxTokens, String strategy, Float customHeadRatio) {
        if (tokens == null) return new ArrayList<>();
        int limit = (maxTokens != null) ? maxTokens : this.maxContextLength;
        int total = tokens.size();
        if (total <= limit) {
            return new ArrayList<>(tokens);
        }

        String strat = (strategy != null) ? strategy : this.defaultStrategy;
        float ratio = (customHeadRatio != null) ? customHeadRatio : this.headRatio;

        List<T> result = new ArrayList<>();
        if (STRATEGY_TAIL.equals(strat) || STRATEGY_SLIDING_WINDOW.equals(strat)) {
            result.addAll(tokens.subList(total - limit, total));
        } else if (STRATEGY_HEAD.equals(strat)) {
            result.addAll(tokens.subList(0, limit));
        } else if (STRATEGY_MIDDLE_OUT.equals(strat)) {
            int headLen = Math.max(1, (int) (limit * ratio));
            int tailLen = limit - headLen;
            if (tailLen <= 0) {
                result.addAll(tokens.subList(0, limit));
            } else {
                result.addAll(tokens.subList(0, headLen));
                result.addAll(tokens.subList(total - tailLen, total));
            }
        } else {
            result.addAll(tokens.subList(total - limit, total));
        }
        return result;
    }
}

