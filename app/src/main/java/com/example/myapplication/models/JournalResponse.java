package com.example.myapplication.models;

import com.google.gson.annotations.SerializedName;

public class JournalResponse {
    private Journal journal;

    public JournalResponse() {}

    public JournalResponse(String id, String content, String mood, String status, String createdAt) {
        this.journal = new Journal(id, content, mood, status, createdAt);
    }

    public Journal getJournal() { return journal; }
    public void setJournal(Journal journal) { this.journal = journal; }

    public String getId() { return journal != null ? journal.getId() : ""; }
    public String getContent() { return journal != null ? journal.getContent() : ""; }
    public String getMood() { return journal != null ? journal.getMood() : ""; }
    public String getStatus() { return journal != null ? journal.getStatus() : ""; }
    public String getCreatedAt() { return journal != null ? journal.getCreatedAt() : ""; }

    public static class Journal {
        private String id;
        private String mood;
        private String content;
        private String status;
        @SerializedName("created_at")
        private String createdAt;

        public Journal() {}

        public Journal(String id, String content, String mood, String status, String createdAt) {
            this.id = id;
            this.content = content;
            this.mood = mood;
            this.status = status;
            this.createdAt = createdAt;
        }

        public String getId() { return id; }
        public String getMood() { return mood; }
        public String getContent() { return content; }
        public String getStatus() { return status; }
        public String getCreatedAt() { return createdAt; }
    }
}