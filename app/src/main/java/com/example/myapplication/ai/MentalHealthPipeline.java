package com.example.myapplication.ai;

import android.content.Context;
import com.example.myapplication.ai.hk.CompositePipeline;
import com.example.myapplication.ai.hk.ContextWindowManager;
import com.example.myapplication.ai.hk.PipelineContext;
import com.example.myapplication.ai.hk.PipelineStage;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * On-Device Hierarchical Mental Health & Welfare AI Pipeline
 * Orchestrated through the HK Neural Composite Pipeline architecture.
 * Combines 3-tier intent routing, VADER micro-sentiment analysis, 24 RAG clinical skills,
 * trajectory tracking, and dynamic empathetic dialogue generation.
 */
public class MentalHealthPipeline {

    private static final List<String> DISTRESS_TERMS = Arrays.asList(
            "hopeless", "helpless", "overwhelmed", "burnt out", "burnout",
            "exhausted", "cannot cope", "breaking down", "isolated", "alone",
            "panic", "anxiety", "nightmare", "cannot sleep", "insomnia", "numb",
            "stress", "stressed", "fatigue", "tired"
    );

    private static final List<String> JOY_TERMS = Arrays.asList(
            "happy", "great", "proud", "good", "relieved", "excited",
            "peaceful", "better", "accomplished", "thankful", "grateful",
            "celebrate", "energy", "optimistic", "glad", "safe", "steady"
    );

    private final ContextWindowManager contextManager;
    private final KnowledgeBase knowledgeBase;
    private final SentimentIntensityAnalyzer sentimentAnalyzer;
    private final HKDistilBertClassifier distilBertClassifier;
    private final HKNeuralLLM neuralLLM;
    private final CompositePipeline compositePipeline;
    private final List<Integer> recentScores = new ArrayList<>();

    public MentalHealthPipeline() {
        this(new ContextWindowManager(2048, ContextWindowManager.STRATEGY_MIDDLE_OUT, 0.25f));
    }

    public MentalHealthPipeline(ContextWindowManager contextManager) {
        this.contextManager = contextManager;
        this.knowledgeBase = new KnowledgeBase();
        this.sentimentAnalyzer = new SentimentIntensityAnalyzer();
        this.distilBertClassifier = new HKDistilBertClassifier(this.knowledgeBase);
        this.neuralLLM = new HKNeuralLLM(this.knowledgeBase);
        this.compositePipeline = new CompositePipeline(contextManager);
        setupPipelineStages();
    }

    public void initializeKnowledgeBase(Context context) {
        knowledgeBase.loadFromContext(context);
    }

    public void initializeKnowledgeBase(java.io.InputStream is) {
        knowledgeBase.loadFromStream(is);
    }

    public KnowledgeBase getKnowledgeBase() {
        return knowledgeBase;
    }

    public SentimentIntensityAnalyzer getSentimentAnalyzer() {
        return sentimentAnalyzer;
    }

    public HKDistilBertClassifier getDistilBertClassifier() {
        return distilBertClassifier;
    }

    public HKNeuralLLM getNeuralLLM() {
        return neuralLLM;
    }

    private void setupPipelineStages() {
        // Stage 1: Crisis Safety Net
        compositePipeline.addStage(new PipelineStage("crisis_safety_stage", "classification", "is_crisis") {
            @Override
            public Object execute(PipelineContext context, Map<String, Object> paramsOverride, ContextWindowManager contextManager) {
                String input = (String) context.get("user_input");
                boolean crisis = CrisisSafetyNet.isCrisis(input);
                context.setOutput(getName(), getOutputKey(), crisis);
                return crisis;
            }
        });

        // Stage 2: Sentiment & DistilBERT Intent Routing
        compositePipeline.addStage(new PipelineStage("intent_sentiment_stage", "nlp", "sentiment_data") {
            @Override
            public Object execute(PipelineContext context, Map<String, Object> paramsOverride, ContextWindowManager contextManager) {
                String input = (String) context.get("user_input");
                Boolean isCrisis = (Boolean) context.get("is_crisis");
                String lower = (input != null) ? input.toLowerCase() : "";

                // 1. DistilBERT sequence classification
                HKDistilBertClassifier.ClassificationResult triage = distilBertClassifier.classify(input);
                context.put("distilbert_triage", triage);
                context.put("distilbert_class", triage.riskClass);
                context.put("distilbert_confidence", triage.confidence);
                context.put("distilbert_rationale", triage.rationale);
                context.put("severity_level", triage.severityLevel);

                // 2. VADER micro-sentiment analysis
                SentimentIntensityAnalyzer.SentimentResult sr = sentimentAnalyzer.analyze(input);

                List<String> signals = new ArrayList<>();
                for (String term : DISTRESS_TERMS) {
                    if (lower.contains(term)) {
                        signals.add(term.replace(" ", "_"));
                    }
                }

                String mood;
                int moraleScore;

                if (Boolean.TRUE.equals(isCrisis) || triage.classIndex == 5) {
                    mood = "emergency";
                    moraleScore = 10;
                    context.put("is_crisis", true);
                } else if (triage.classIndex >= 2 || !signals.isEmpty() || sr.moraleScore < 42) {
                    mood = "triage";
                    moraleScore = Math.max(15, Math.min(50, sr.moraleScore - (triage.severityLevel * 5)));
                } else if (hasJoyTerms(lower) || sr.moraleScore > 62) {
                    mood = "joy";
                    moraleScore = Math.max(65, Math.min(98, sr.moraleScore));
                } else {
                    mood = "triage";
                    moraleScore = Math.max(40, Math.min(65, sr.moraleScore));
                }

                Map<String, Object> data = new HashMap<>();
                data.put("mood", mood);
                data.put("morale_score", moraleScore);
                data.put("compound", sr.compound);
                data.put("signals", signals);
                data.put("distilbert_class", triage.riskClass);
                data.put("distilbert_confidence", triage.confidence);

                context.setOutput(getName(), getOutputKey(), data);
                context.put("mood", mood);
                context.put("morale_score", moraleScore);
                context.put("signals", signals);
                return data;
            }
        });

        // Stage 3: RAG Retrieval from Clinical Knowledge Base
        compositePipeline.addStage(new PipelineStage("rag_retrieval_stage", "rag", "rag_result") {
            @Override
            public Object execute(PipelineContext context, Map<String, Object> paramsOverride, ContextWindowManager contextManager) {
                String input = (String) context.get("user_input");
                KnowledgeBase.SearchResult match = knowledgeBase.search(input, 0.25f, 450);
                context.setOutput(getName(), getOutputKey(), match);
                context.put("matched_protocol", match != null ? match.title : null);
                context.put("cosine_score", match != null ? match.score : 0.0f);
                context.put("rag_protocol", match);
                return match;
            }
        });

        // Stage 4: Longitudinal Trajectory Tracking
        compositePipeline.addStage(new PipelineStage("trajectory_stage", "analytics", "trajectory_trend") {
            @Override
            public Object execute(PipelineContext context, Map<String, Object> paramsOverride, ContextWindowManager contextManager) {
                Integer score = (Integer) context.get("morale_score");
                if (score != null) {
                    recentScores.add(score);
                    if (recentScores.size() > 10) {
                        recentScores.remove(0);
                    }
                }
                String trend = computeTrajectory(recentScores);
                context.setOutput(getName(), getOutputKey(), trend);
                context.put("trajectory_trend", trend);
                return trend;
            }
        });

        // Stage 5: Neural Generative LLM & Empathetic Dialogue Stage
        compositePipeline.addStage(new PipelineStage("empathetic_generation_stage", "generation", "generated_response") {
            @Override
            public Object execute(PipelineContext context, Map<String, Object> paramsOverride, ContextWindowManager contextManager) {
                String input = (String) context.get("user_input");
                HKDistilBertClassifier.ClassificationResult triage =
                        (HKDistilBertClassifier.ClassificationResult) context.get("distilbert_triage");
                KnowledgeBase.SearchResult rag = (KnowledgeBase.SearchResult) context.get("rag_result");
                String trend = (String) context.get("trajectory_trend");
                Integer morale = (Integer) context.get("morale_score");

                // Generate response using on-device Neural LLM
                String response = neuralLLM.generateResponse(
                        input,
                        triage,
                        rag,
                        morale != null ? morale : 50,
                        trend != null ? trend : "STABLE"
                );

                context.setOutput(getName(), getOutputKey(), response);
                context.put("generated_text", response);
                context.put("response_text", response);
                context.put("response", response);
                return response;
            }
        });
    }

    private static boolean hasJoyTerms(String text) {
        for (String j : JOY_TERMS) {
            if (text.contains(j)) return true;
        }
        return false;
    }

    public static String computeTrajectory(List<Integer> scores) {
        if (scores == null || scores.size() < 2) {
            return "STABLE";
        }
        int delta = scores.get(scores.size() - 1) - scores.get(0);
        int lastScore = scores.get(scores.size() - 1);
        double recentAvg = (scores.get(scores.size() - 1) + scores.get(scores.size() - 2)) / 2.0;

        if (delta <= -20 || lastScore < 25) {
            return "RAPIDLY DECLINING (Warning)";
        } else if (delta < -8 || recentAvg < 40) {
            return "DECLINING";
        } else if (delta >= 20 || lastScore > 80) {
            return "RAPIDLY IMPROVING";
        } else if (delta > 8 || recentAvg > 65) {
            return "IMPROVING";
        } else {
            return "STABLE";
        }
    }

    private String synthesizeResponse(String input, boolean isCrisis, String mood, KnowledgeBase.SearchResult rag, String trend, int morale) {
        if (isCrisis) {
            return "I hear how much pain you are carrying right now, and I want you to know you are not alone in this. " +
                   "What you are experiencing matters deeply. Please stay safe — an immediate human support option is available " +
                   "right now through the Get Support button or your unit medical officer. Please connect with someone who can " +
                   "be beside you through this moment.";
        }

        if ("joy".equals(mood)) {
            return "That is really great to hear! It is rewarding to see positive moments like this on duty. " +
                   "Holding onto those wins and sharing them with comrades makes a big difference. How has the rest of your day been shaping up?";
        }

        // Triage / Stress with RAG grounding
        if (rag != null) {
            String title = rag.title.toLowerCase();
            if (title.contains("sleep") || title.contains("fatigue")) {
                return "Thank you for sharing that with me. Operational shifts and disrupted sleep take a serious toll on both alertness " +
                       "and mood. When your body doesn't get enough recovery, even standard tasks feel heavier. If possible today, try to grab " +
                       "a quiet 20-minute rest block, drink some water, and remember you don't have to carry everything at once. What part of your schedule feels heaviest right now?";
            } else if (title.contains("family") || title.contains("separation")) {
                return "It takes courage to put that into words. Being separated from family during deployments and transfers is one of the " +
                       "heaviest aspects of service. It is completely normal to feel that pull. Have you been able to speak with them recently, " +
                       "or is there a comrade or welfare representative nearby who knows what you're facing?";
            } else if (title.contains("operational") || title.contains("stress")) {
                return "Operational stress under sustained tempo is very real, and recognizing it is an important first step. " +
                       "Your dedication to the unit is evident, but you also need room to breathe and recharge. Let's take it one step at a time — " +
                       "what is one small thing you can take off your plate or get support with today?";
            }
        }

        return "Thank you for reaching out and sharing that with me. What you're describing carries real weight, and it's completely " +
               "understandable to feel strained under these conditions. Taking a moment to pause and reflect is a sign of resilience, " +
               "not weakness. Would it help to talk more about what brought this up today?";
    }

    /**
     * Executes the complete on-device HK pipeline turn.
     */
    public PipelineContext run(String userInput) {
        Map<String, Object> initial = new HashMap<>();
        initial.put("user_input", userInput);
        return compositePipeline.run(initial);
    }
}
