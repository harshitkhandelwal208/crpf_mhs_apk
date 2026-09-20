package com.example.myapplication.ai;

import android.content.Context;
import android.os.Bundle;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.util.Log;

import java.util.Locale;

/**
 * On-Device Text-to-Speech (TTS) Manager for CRPF MHS.
 * Enables hands-free audio readouts of AI companion responses,
 * guided relaxation protocols, and crisis helpline numbers.
 * 100% offline, private, and latency-free.
 */
public class SentinelTTSManager implements TextToSpeech.OnInitListener {

    private static final String TAG = "SentinelTTSManager";
    private TextToSpeech textToSpeech;
    private boolean isInitialized = false;
    private final Context context;
    private TTSStateListener stateListener;

    public interface TTSStateListener {
        void onSpeechStarted();
        void onSpeechCompleted();
        void onSpeechError(String message);
    }

    public SentinelTTSManager(Context context) {
        this.context = context.getApplicationContext();
        initTTS();
    }

    private void initTTS() {
        try {
            textToSpeech = new TextToSpeech(context, this);
        } catch (Exception e) {
            Log.e(TAG, "Failed to instantiate TextToSpeech: " + e.getMessage());
        }
    }

    public void setStateListener(TTSStateListener listener) {
        this.stateListener = listener;
    }

    @Override
    public void onInit(int status) {
        if (status == TextToSpeech.SUCCESS && textToSpeech != null) {
            int result = textToSpeech.setLanguage(Locale.ENGLISH);
            if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
                // Fallback to default locale
                textToSpeech.setLanguage(Locale.getDefault());
            }

            // Calibrated for calming, measured clinical cadence
            textToSpeech.setPitch(1.0f);
            textToSpeech.setSpeechRate(0.92f);

            textToSpeech.setOnUtteranceProgressListener(new UtteranceProgressListener() {
                @Override
                public void onStart(String utteranceId) {
                    if (stateListener != null) {
                        stateListener.onSpeechStarted();
                    }
                }

                @Override
                public void onDone(String utteranceId) {
                    if (stateListener != null) {
                        stateListener.onSpeechCompleted();
                    }
                }

                @Override
                @SuppressWarnings("deprecation")
                public void onError(String utteranceId) {
                    if (stateListener != null) {
                        stateListener.onSpeechError("Audio synthesis encountered an issue.");
                    }
                }

                @Override
                public void onError(String utteranceId, int errorCode) {
                    if (stateListener != null) {
                        stateListener.onSpeechError("Audio synthesis error code: " + errorCode);
                    }
                }
            });

            isInitialized = true;
            Log.i(TAG, "TextToSpeech initialized successfully.");
        } else {
            isInitialized = false;
            Log.w(TAG, "TextToSpeech initialization failed with status: " + status);
        }
    }

    /**
     * Speaks the provided text aloud.
     */
    public synchronized boolean speak(String text) {
        if (!isInitialized || textToSpeech == null || text == null || text.trim().isEmpty()) {
            return false;
        }

        // Clean out protocol metadata tags if present before speaking
        String cleanText = text.replaceAll("\\[Protocol:[^\\]]+\\]", "").trim();

        Bundle params = new Bundle();
        params.putString(TextToSpeech.Engine.KEY_PARAM_UTTERANCE_ID, "sentinel_tts_" + System.currentTimeMillis());

        int res = textToSpeech.speak(cleanText, TextToSpeech.QUEUE_FLUSH, params, params.getString(TextToSpeech.Engine.KEY_PARAM_UTTERANCE_ID));
        return res == TextToSpeech.SUCCESS;
    }

    /**
     * Stops current speech immediately.
     */
    public synchronized void stop() {
        if (textToSpeech != null) {
            textToSpeech.stop();
        }
        if (stateListener != null) {
            stateListener.onSpeechCompleted();
        }
    }

    public synchronized boolean isSpeaking() {
        return textToSpeech != null && textToSpeech.isSpeaking();
    }

    /**
     * Shuts down the TTS engine and releases audio resources.
     */
    public synchronized void shutdown() {
        if (textToSpeech != null) {
            textToSpeech.stop();
            textToSpeech.shutdown();
            textToSpeech = null;
        }
        isInitialized = false;
    }
}
