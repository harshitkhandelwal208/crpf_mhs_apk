package com.example.myapplication.auth;

import java.io.IOException;

import okhttp3.Interceptor;
import okhttp3.Request;
import okhttp3.Response;

public class AuthInterceptor implements Interceptor {
    private final AuthManager authManager;

    public AuthInterceptor(AuthManager authManager) {
        this.authManager = authManager;
    }

    @Override
    public Response intercept(Chain chain) throws IOException {
        Request original = chain.request();
        
        // Skip adding token if request already has an Authorization header
        if (original.header("Authorization") != null) {
            return chain.proceed(original);
        }

        String accessToken = authManager.getAccessToken();
        if (accessToken != null) {
            Request authorized = original.newBuilder()
                    .header("Authorization", "Bearer " + accessToken)
                    .build();
            return chain.proceed(authorized);
        }

        return chain.proceed(original);
    }
}
