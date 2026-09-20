package com.example.myapplication.auth;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

import com.example.myapplication.api.SentinelApiService;
import com.example.myapplication.models.RefreshRequest;
import com.example.myapplication.models.TokenResponse;

import java.io.IOException;
import java.util.concurrent.TimeUnit;

import okhttp3.Authenticator;
import okhttp3.ConnectionPool;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.ResponseBody;
import okhttp3.Route;
import retrofit2.Call;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;

public class TokenAuthenticator implements Authenticator {
    private final AuthManager authManager;
    private final SentinelApiService refreshService;

    public TokenAuthenticator(AuthManager authManager, String baseUrl) {
        this.authManager = authManager;
        OkHttpClient refreshClient = new OkHttpClient.Builder()
                .connectTimeout(10, TimeUnit.SECONDS)
                .readTimeout(15, TimeUnit.SECONDS)
                .writeTimeout(15, TimeUnit.SECONDS)
                .callTimeout(20, TimeUnit.SECONDS)
                .connectionPool(new ConnectionPool(2, 2, TimeUnit.MINUTES))
                .retryOnConnectionFailure(true)
                .build();
        refreshService = new Retrofit.Builder()
                .baseUrl(baseUrl)
                .client(refreshClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .create(SentinelApiService.class);
    }

    @Nullable
    @Override
    public synchronized Request authenticate(@Nullable Route route, @NonNull Response response) throws IOException {
        if (responseCount(response) >= 2) {
            return null;
        }

        String currentAccessToken = authManager.getAccessToken();
        String requestAuthorization = response.request().header("Authorization");
        if (currentAccessToken != null
                && !("Bearer " + currentAccessToken).equals(requestAuthorization)) {
            return response.request().newBuilder()
                    .header("Authorization", "Bearer " + currentAccessToken)
                    .build();
        }

        String refreshToken = authManager.getRefreshToken();
        if (refreshToken == null || refreshToken.trim().isEmpty()) {
            return null;
        }

        Call<TokenResponse> call = refreshService.refreshToken(new RefreshRequest(refreshToken));
        retrofit2.Response<TokenResponse> refreshResponse = call.execute();
        try {
            TokenResponse tokens = refreshResponse.body();
            if (refreshResponse.isSuccessful()
                    && tokens != null
                    && tokens.getAccessToken() != null
                    && !tokens.getAccessToken().trim().isEmpty()) {
                authManager.saveTokens(tokens.getAccessToken(), tokens.getRefreshToken());
                return response.request().newBuilder()
                        .header("Authorization", "Bearer " + tokens.getAccessToken())
                        .build();
            }

            int code = refreshResponse.code();
            if (code == 400 || code == 401 || code == 403) {
                authManager.clearTokens();
            }
            return null;
        } finally {
            ResponseBody errorBody = refreshResponse.errorBody();
            if (errorBody != null) {
                errorBody.close();
            }
        }
    }

    private int responseCount(Response response) {
        int result = 1;
        while ((response = response.priorResponse()) != null) {
            result++;
        }
        return result;
    }
}
