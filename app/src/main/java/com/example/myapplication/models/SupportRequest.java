package com.example.myapplication.models;

public class SupportRequest {
    private final String type;
    private final String message;

    public SupportRequest(String type, String message) {
        this.type = type;
        this.message = message;
    }
}