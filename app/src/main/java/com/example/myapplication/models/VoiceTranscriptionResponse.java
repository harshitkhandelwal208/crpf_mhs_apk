package com.example.myapplication.models;

public class VoiceTranscriptionResponse {
    private String id;
    private String transcript;
    private boolean requires_review;

    public String getId() { return id; }
    public String getTranscript() { return transcript; }
    public boolean isRequiresReview() { return requires_review; }
}