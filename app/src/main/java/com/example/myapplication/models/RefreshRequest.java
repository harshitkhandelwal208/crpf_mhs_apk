package com.example.myapplication.models;

import com.google.gson.annotations.SerializedName;

public class RefreshRequest {
    @SerializedName("refresh_token")
    private final String refreshToken;

    public RefreshRequest(String refreshToken) {
        this.refreshToken = refreshToken;
    }

    public String getRefreshToken() {
        return refreshToken;
    }
}
