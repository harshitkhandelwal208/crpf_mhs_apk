package com.example.myapplication.models;

public class ChatRequest {
    private final String message;
    private final String conversation_id;

    public ChatRequest(String message, String conversationId) {
        this.message = message;
        this.conversation_id = conversationId;
    }
}