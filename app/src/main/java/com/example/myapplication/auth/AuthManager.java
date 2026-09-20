package com.example.myapplication.auth;

import android.content.Context;
import android.content.SharedPreferences;

import androidx.security.crypto.EncryptedSharedPreferences;
import androidx.security.crypto.MasterKey;

import java.io.IOException;
import java.security.GeneralSecurityException;

public class AuthManager {
    private static final String LEGACY_PREF_NAME = "SentinelAuthPrefs";
    private static final String SECURE_PREF_NAME = "SentinelAuthSecurePrefs";
    private static final String KEY_ACCESS_TOKEN = "access_token";
    private static final String KEY_REFRESH_TOKEN = "refresh_token";
    private static final String KEY_OFFLINE_SESSION = "offline_session";
    private static final String LEGACY_OFFLINE_TOKEN_PREFIX = "offline_token_";

    private final SharedPreferences prefs;

    public AuthManager(Context context) {
        Context appContext = context.getApplicationContext();
        prefs = createSecurePreferences(appContext);
        migrateLegacyPreferences(appContext);
        removeLegacySyntheticToken();
    }

    public void saveTokens(String accessToken, String refreshToken) {
        if (accessToken == null || accessToken.trim().isEmpty()) {
            clearTokens();
            return;
        }
        prefs.edit()
                .putString(KEY_ACCESS_TOKEN, accessToken)
                .putString(KEY_REFRESH_TOKEN, refreshToken)
                .putBoolean(KEY_OFFLINE_SESSION, false)
                .apply();
    }

    public void saveOfflineSession() {
        prefs.edit()
                .remove(KEY_ACCESS_TOKEN)
                .remove(KEY_REFRESH_TOKEN)
                .putBoolean(KEY_OFFLINE_SESSION, true)
                .apply();
    }

    public String getAccessToken() {
        return prefs.getString(KEY_ACCESS_TOKEN, null);
    }

    public String getRefreshToken() {
        return prefs.getString(KEY_REFRESH_TOKEN, null);
    }

    public boolean hasCloudSession() {
        return getAccessToken() != null;
    }

    public void clearTokens() {
        prefs.edit().clear().apply();
    }

    public boolean isLoggedIn() {
        return hasCloudSession() || prefs.getBoolean(KEY_OFFLINE_SESSION, false);
    }

    @SuppressWarnings("deprecation")
    private static SharedPreferences createSecurePreferences(Context context) {
        try {
            MasterKey masterKey = new MasterKey.Builder(context)
                    .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
                    .build();
            return EncryptedSharedPreferences.create(
                    context,
                    SECURE_PREF_NAME,
                    masterKey,
                    EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                    EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
            );
        } catch (GeneralSecurityException | IOException exception) {
            throw new IllegalStateException("Secure authentication storage is unavailable", exception);
        }
    }

    private void migrateLegacyPreferences(Context context) {
        SharedPreferences legacy = context.getSharedPreferences(LEGACY_PREF_NAME, Context.MODE_PRIVATE);
        if (legacy.getAll().isEmpty()) {
            return;
        }

        String accessToken = legacy.getString(KEY_ACCESS_TOKEN, null);
        String refreshToken = legacy.getString(KEY_REFRESH_TOKEN, null);
        if (accessToken != null && !accessToken.startsWith(LEGACY_OFFLINE_TOKEN_PREFIX)) {
            prefs.edit()
                    .putString(KEY_ACCESS_TOKEN, accessToken)
                    .putString(KEY_REFRESH_TOKEN, refreshToken)
                    .putBoolean(KEY_OFFLINE_SESSION, false)
                    .commit();
        }
        legacy.edit().clear().apply();
    }

    private void removeLegacySyntheticToken() {
        String accessToken = getAccessToken();
        if (accessToken != null && accessToken.startsWith(LEGACY_OFFLINE_TOKEN_PREFIX)) {
            clearTokens();
        }
    }
}
