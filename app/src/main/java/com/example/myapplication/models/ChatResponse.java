package com.example.myapplication.models;

import com.google.gson.annotations.SerializedName;

public class ChatResponse {
    @SerializedName("conversation_id")
    private String conversationId;
    private Message message;
    @SerializedName("support_escalation")
    private boolean supportEscalation;

    public ChatResponse() {}

    public ChatResponse(String conversationId, String content, boolean supportEscalation) {
        this.conversationId = conversationId;
        this.message = new Message(content);
        this.supportEscalation = supportEscalation;
    }

    public String getConversationId() { return conversationId; }
    public Message getMessage() { return message; }
    public boolean isSupportEscalation() { return supportEscalation; }

    public static class Message {
        private String id;
        private String role;
        private String content;

        public Message() {}

        public Message(String content) {
            this.id = java.util.UUID.randomUUID().toString();
            this.role = "assistant";
            this.content = content;
        }

        public String getId() { return id; }
        public String getRole() { return role; }
        public String getContent() { return content; }
    }
}