package com.example.myapplication.models;

import com.google.gson.annotations.SerializedName;

public class JournalResponse {
    private Journal journal;

    public Journal getJournal() { return journal; }

    public static class Journal {
        private String id;
        private String mood;
        private String content;
        private String status;
        @SerializedName("created_at")
        private String createdAt;

        public String getId() { return id; }
        public String getMood() { return mood; }
        public String getContent() { return content; }
        public String getStatus() { return status; }
        public String getCreatedAt() { return createdAt; }
    }
}