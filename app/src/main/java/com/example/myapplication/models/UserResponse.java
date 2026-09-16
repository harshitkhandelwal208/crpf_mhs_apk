package com.example.myapplication.models;

import com.google.gson.annotations.SerializedName;

public class UserResponse {
    @SerializedName("id")
    private String id;

    @SerializedName("email")
    private String email;

    @SerializedName("name")
    private String fullName;

    @SerializedName("role")
    private String role;

    @SerializedName("onboarding_complete")
    private boolean onboardingComplete;

    @SerializedName("mfa_enabled")
    private boolean mfaEnabled;

    public String getId() { return id; }
    public String getEmail() { return email; }
    public String getFullName() { return fullName; }
    public String getRole() { return role; }
    public boolean isOnboardingComplete() { return onboardingComplete; }
    public boolean isMfaEnabled() { return mfaEnabled; }
}
