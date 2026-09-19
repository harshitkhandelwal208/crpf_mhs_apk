package com.example.myapplication.ai;

import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

/**
 * VADER-Calibrated Lexical Sentiment Intensity Analyzer
 * Ported to Java for on-device, real-time micro-morale scoring.
 * Implements valence lookup, negation detection, capitalization amplification,
 * and normalized compound scoring.
 */
public class SentimentIntensityAnalyzer {

    private static final float B_INCR = 0.293f;
    private static final float B_DECR = -0.293f;
    private static final float C_INCR = 0.733f;
    private static final float N_SCALAR = -0.74f;

    private static final Set<String> NEGATIONS = new HashSet<>(Arrays.asList(
            "not", "never", "no", "neither", "nor", "barely", "hardly", "scarcely",
            "rarely", "seldom", "despite", "without", "can't", "cannot", "won't",
            "don't", "didn't", "isnt", "isn't", "arent", "aren't"
    ));

    private static final Map<String, Float> BOOSTER_DICT = new HashMap<>();
    private static final Map<String, Float> LEXICON = new HashMap<>();

    static {
        // Boosters
        BOOSTER_DICT.put("absolutely", B_INCR);
        BOOSTER_DICT.put("incredibly", B_INCR);
        BOOSTER_DICT.put("extremely", B_INCR);
        BOOSTER_DICT.put("really", B_INCR);
        BOOSTER_DICT.put("so", B_INCR);
        BOOSTER_DICT.put("very", B_INCR);
        BOOSTER_DICT.put("severely", B_INCR);
        BOOSTER_DICT.put("totally", B_INCR);
        BOOSTER_DICT.put("barely", B_DECR);
        BOOSTER_DICT.put("hardly", B_DECR);
        BOOSTER_DICT.put("somewhat", B_DECR);
        BOOSTER_DICT.put("slightly", B_DECR);

        // Core clinical & morale lexicon
        LEXICON.put("great", 3.1f);
        LEXICON.put("good", 2.0f);
        LEXICON.put("happy", 2.7f);
        LEXICON.put("proud", 2.4f);
        LEXICON.put("excited", 2.6f);
        LEXICON.put("relieved", 2.1f);
        LEXICON.put("safe", 2.2f);
        LEXICON.put("steady", 1.9f);
        LEXICON.put("calm", 1.8f);
        LEXICON.put("peaceful", 2.2f);
        LEXICON.put("grateful", 2.5f);
        LEXICON.put("thankful", 2.3f);
        LEXICON.put("strong", 2.2f);
        LEXICON.put("alert", 1.5f);
        LEXICON.put("accomplished", 2.6f);
        LEXICON.put("better", 1.9f);
        LEXICON.put("hopeful", 2.3f);
        LEXICON.put("supported", 2.5f);

        // Distress / Negative
        LEXICON.put("bad", -2.5f);
        LEXICON.put("tired", -1.8f);
        LEXICON.put("exhausted", -2.9f);
        LEXICON.put("fatigue", -2.4f);
        LEXICON.put("stress", -2.3f);
        LEXICON.put("stressed", -2.5f);
        LEXICON.put("overwhelmed", -3.1f);
        LEXICON.put("hopeless", -3.4f);
        LEXICON.put("helpless", -3.2f);
        LEXICON.put("anxious", -2.6f);
        LEXICON.put("anxiety", -2.8f);
        LEXICON.put("panic", -3.2f);
        LEXICON.put("depressed", -3.3f);
        LEXICON.put("sad", -2.1f);
        LEXICON.put("alone", -2.4f);
        LEXICON.put("isolated", -2.7f);
        LEXICON.put("burnout", -3.0f);
        LEXICON.put("numb", -2.2f);
        LEXICON.put("nightmare", -3.0f);
        LEXICON.put("insomnia", -2.6f);
        LEXICON.put("struggling", -2.7f);
        LEXICON.put("pain", -2.8f);
        LEXICON.put("hurt", -2.5f);
        LEXICON.put("heavy", -1.6f);
        LEXICON.put("difficult", -1.7f);
        LEXICON.put("demanding", -1.5f);
        LEXICON.put("tough", -1.4f);
    }

    public static class SentimentResult {
        public final float compound;
        public final float positive;
        public final float negative;
        public final float neutral;
        public final int moraleScore;

        public SentimentResult(float compound, float positive, float negative, float neutral, int moraleScore) {
            this.compound = compound;
            this.positive = positive;
            this.negative = negative;
            this.neutral = neutral;
            this.moraleScore = moraleScore;
        }
    }

    public SentimentResult analyze(String text) {
        if (text == null || text.trim().isEmpty()) {
            return new SentimentResult(0.0f, 0.0f, 0.0f, 1.0f, 50);
        }

        String[] words = text.split("\\s+");
        float sumValence = 0.0f;
        int sentimentWordsCount = 0;
        float posScore = 0.0f;
        float negScore = 0.0f;

        for (int i = 0; i < words.length; i++) {
            String rawWord = words[i].replaceAll("[^a-zA-Z']", "");
            String lower = rawWord.toLowerCase();

            if (LEXICON.containsKey(lower)) {
                float valence = LEXICON.get(lower);

                // All caps boost
                if (rawWord.equals(rawWord.toUpperCase()) && rawWord.length() > 1) {
                    if (valence > 0) valence += C_INCR;
                    else valence -= C_INCR;
                }

                // Check preceding words for negations or boosters
                for (int j = 1; j <= 3 && (i - j) >= 0; j++) {
                    String prev = words[i - j].replaceAll("[^a-zA-Z']", "").toLowerCase();
                    if (BOOSTER_DICT.containsKey(prev)) {
                        float b = BOOSTER_DICT.get(prev);
                        if (valence < 0) b = -b;
                        valence += b;
                    }
                    if (NEGATIONS.contains(prev)) {
                        valence = valence * N_SCALAR;
                    }
                }

                if (valence > 0) posScore += valence;
                else if (valence < 0) negScore += Math.abs(valence);

                sumValence += valence;
                sentimentWordsCount++;
            }
        }

        // Punctuation emphasis
        int exclamations = 0;
        for (char c : text.toCharArray()) {
            if (c == '!') exclamations++;
        }
        if (exclamations > 0) {
            float punctBoost = Math.min(exclamations * 0.15f, 0.6f);
            if (sumValence > 0) sumValence += punctBoost;
            else if (sumValence < 0) sumValence -= punctBoost;
        }

        // Normalize compound: sum / sqrt(sum^2 + alpha)
        float compound = (float) (sumValence / Math.sqrt((sumValence * sumValence) + 15.0));
        compound = Math.max(-1.0f, Math.min(1.0f, compound));

        // Morale score 0-100
        int morale = Math.round(((compound + 1.0f) / 2.0f) * 90.0f + 10.0f);
        morale = Math.max(10, Math.min(98, morale));

        float totalScore = posScore + negScore + Math.max(1, words.length - sentimentWordsCount);
        float posNorm = posScore / totalScore;
        float negNorm = negScore / totalScore;
        float neuNorm = 1.0f - (posNorm + negNorm);

        return new SentimentResult(compound, posNorm, negNorm, neuNorm, morale);
    }

    public int getMoraleScore(String text) {
        return analyze(text).moraleScore;
    }
}
