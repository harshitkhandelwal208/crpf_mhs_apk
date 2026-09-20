package com.example.myapplication.models;

import com.google.gson.annotations.SerializedName;

public class JournalRequest {
    private final String content;
    private final String mood;
    private final String status;

    @SerializedName("client_request_id")
    private final String clientRequestId;

    public JournalRequest(String content, String mood, String status) {
        this(content, mood, status, null);
    }

    public JournalRequest(String content, String mood, String status, String clientRequestId) {
        this.content = content;
        this.mood = mood;
        this.status = status;
        this.clientRequestId = clientRequestId;
    }

    public String getClientRequestId() {
        return clientRequestId;
    }
}
