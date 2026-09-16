package com.example.myapplication.auth;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

import com.example.myapplication.api.SentinelApiService;
import com.example.myapplication.models.RefreshRequest;
import com.example.myapplication.models.TokenResponse;

import java.io.IOException;

import okhttp3.Authenticator;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.Route;
import retrofit2.Call;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;

public class TokenAuthenticator implements Authenticator {
    private final AuthManager authManager;
    private final String baseUrl;

    public TokenAuthenticator(AuthManager authManager, String baseUrl) {
        this.authManager = authManager;
        this.baseUrl = baseUrl;
    }

    @Nullable
    @Override
    public Request authenticate(@Nullable Route route, @NonNull Response response) throws IOException {
        // Only try to authenticate if we haven't tried yet for this request
        if (responseCount(response) >= 2) {
            return null;
        }

        String refreshToken = authManager.getRefreshToken();
        if (refreshToken == null) {
            return null;
        }

        // We need a separate Retrofit instance for the refresh call to avoid circularity
        // and because we don't want the AuthInterceptor to add the old Bearer token to this request.
        Retrofit retrofit = new Retrofit.Builder()
                .baseUrl(baseUrl)
                .addConverterFactory(GsonConverterFactory.create())
                .build();

        SentinelApiService apiService = retrofit.create(SentinelApiService.class);
        Call<TokenResponse> call = apiService.refreshToken(new RefreshRequest(refreshToken));
        
        retrofit2.Response<TokenResponse> refreshResponse = call.execute();

        if (refreshResponse.isSuccessful() && refreshResponse.body() != null) {
            TokenResponse tokens = refreshResponse.body();
            authManager.saveTokens(tokens.getAccessToken(), tokens.getRefreshToken());

            return response.request().newBuilder()
                    .header("Authorization", "Bearer " + tokens.getAccessToken())
                    .build();
        } else {
            // Refresh failed, clear tokens so user is forced to log in again
            authManager.clearTokens();
            return null;
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
