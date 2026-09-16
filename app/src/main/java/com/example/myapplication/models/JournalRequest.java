package com.example.myapplication.models;

public class JournalRequest {
    private final String content;
    private final String mood;
    private final String status;

    public JournalRequest(String content, String mood, String status) {
        this.content = content;
        this.mood = mood;
        this.status = status;
    }
}