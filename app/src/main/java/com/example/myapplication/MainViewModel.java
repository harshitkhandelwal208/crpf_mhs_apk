package com.example.myapplication;

import androidx.annotation.NonNull;
import androidx.lifecycle.LiveData;
import androidx.lifecycle.MutableLiveData;
import androidx.lifecycle.ViewModel;
import androidx.lifecycle.ViewModelProvider;

import com.example.myapplication.api.SentinelApiService;
import com.example.myapplication.auth.AuthManager;
import com.example.myapplication.models.LoginRequest;
import com.example.myapplication.models.TokenResponse;
import com.example.myapplication.models.UserResponse;
import com.example.myapplication.models.ChatRequest;
import com.example.myapplication.models.ChatResponse;
import com.example.myapplication.models.JournalRequest;
import com.example.myapplication.models.JournalResponse;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class MainViewModel extends ViewModel {

    private static final String PERSONNEL_ROLE = "PERSONNEL";

    private final AuthManager authManager;
    private final SentinelApiService apiService;

    private final MutableLiveData<Boolean> _isLoggedIn = new MutableLiveData<>();
    public final LiveData<Boolean> isLoggedIn = _isLoggedIn;

    private final MutableLiveData<UserResponse> _userProfile = new MutableLiveData<>();
    public final LiveData<UserResponse> userProfile = _userProfile;

    private final MutableLiveData<Boolean> _isLoading = new MutableLiveData<>(false);
    public final LiveData<Boolean> isLoading = _isLoading;

    private final MutableLiveData<Integer> _errorMessageResId = new MutableLiveData<>();
    public final LiveData<Integer> errorMessageResId = _errorMessageResId;

    public MainViewModel(AuthManager authManager, SentinelApiService apiService) {
        this.authManager = authManager;
        this.apiService = apiService;
        _isLoggedIn.setValue(authManager.isLoggedIn());
    }

    public void login(String email, String password) {
        _errorMessageResId.setValue(null);
        _isLoading.setValue(true);

        apiService.login(new LoginRequest(email, password)).enqueue(new Callback<>() {
            @Override
            public void onResponse(@NonNull Call<TokenResponse> call, @NonNull Response<TokenResponse> response) {
                _isLoading.setValue(false);
                if (!response.isSuccessful() || response.body() == null) {
                    _errorMessageResId.setValue(response.code() == 401
                            ? R.string.error_invalid_credentials
                            : R.string.error_generic_login);
                    return;
                }

                TokenResponse tokens = response.body();
                authManager.saveTokens(tokens.getAccessToken(), tokens.getRefreshToken());
                _isLoggedIn.setValue(true);
                loadProfile();
            }

            @Override
            public void onFailure(@NonNull Call<TokenResponse> call, @NonNull Throwable throwable) {
                _isLoading.setValue(false);
                _errorMessageResId.setValue(R.string.error_connection);
            }
        });
    }

    public void loadProfile() {
        _isLoading.setValue(true);
        apiService.getUserProfile().enqueue(new Callback<>() {
            @Override
            public void onResponse(@NonNull Call<UserResponse> call, @NonNull Response<UserResponse> response) {
                _isLoading.setValue(false);
                if (!response.isSuccessful() || response.body() == null) {
                    logout();
                    _errorMessageResId.setValue(R.string.error_session_expired);
                    return;
                }

                UserResponse user = response.body();
                if (!PERSONNEL_ROLE.equals(user.getRole())) {
                    logout();
                    _errorMessageResId.setValue(R.string.error_personnel_only);
                    return;
                }
                _userProfile.setValue(user);
            }

            @Override
            public void onFailure(@NonNull Call<UserResponse> call, @NonNull Throwable throwable) {
                _isLoading.setValue(false);
                logout();
                _errorMessageResId.setValue(R.string.error_load_profile);
            }
        });
    }

    public void logout() {
        authManager.clearTokens();
        _isLoggedIn.setValue(false);
        _userProfile.setValue(null);
    }

    public void clearError() {
        _errorMessageResId.setValue(null);
    }

    public void sendChat(String message, String conversationId, Callback<ChatResponse> callback) {
        apiService.sendChat(new ChatRequest(message, conversationId)).enqueue(callback);
    }

    public void saveJournal(String content, String mood, String status, Callback<JournalResponse> callback) {
        apiService.createJournal(new JournalRequest(content, mood, status)).enqueue(callback);
    }

    public static class Factory implements ViewModelProvider.Factory {
        private final AuthManager authManager;
        private final SentinelApiService apiService;

        public Factory(AuthManager authManager, SentinelApiService apiService) {
            this.authManager = authManager;
            this.apiService = apiService;
        }

        @NonNull
        @Override
        public <T extends ViewModel> T create(@NonNull Class<T> modelClass) {
            if (modelClass.isAssignableFrom(MainViewModel.class)) {
                return (T) new MainViewModel(authManager, apiService);
            }
            throw new IllegalArgumentException("Unknown ViewModel class");
        }
    }
}
