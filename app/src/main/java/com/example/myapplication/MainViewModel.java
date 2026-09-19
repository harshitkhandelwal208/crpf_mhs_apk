package com.example.myapplication;

import android.content.Context;
import androidx.annotation.NonNull;
import androidx.lifecycle.LiveData;
import androidx.lifecycle.MutableLiveData;
import androidx.lifecycle.ViewModel;
import androidx.lifecycle.ViewModelProvider;

import com.example.myapplication.ai.MentalHealthPipeline;
import com.example.myapplication.ai.hk.PipelineContext;
import com.example.myapplication.api.SentinelApiService;
import com.example.myapplication.auth.AuthManager;
import com.example.myapplication.data.LocalRepository;
import com.example.myapplication.models.LoginRequest;
import com.example.myapplication.models.TokenResponse;
import com.example.myapplication.models.UserResponse;
import com.example.myapplication.models.ChatRequest;
import com.example.myapplication.models.ChatResponse;
import com.example.myapplication.models.JournalRequest;
import com.example.myapplication.models.JournalResponse;

import java.util.List;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

/**
 * MainViewModel for CRPF MHS Mobile App
 * Supports Standalone On-Device AI Mode (HK Neural Composite Pipeline & Local SQLite)
 * with graceful Online Sync when a backend server is reachable.
 */
public class MainViewModel extends ViewModel {

    private static final String PERSONNEL_ROLE = "PERSONNEL";

    private final AuthManager authManager;
    private final SentinelApiService apiService;
    private final LocalRepository localRepo;
    private final MentalHealthPipeline pipeline;

    private final MutableLiveData<Boolean> _isLoggedIn = new MutableLiveData<>();
    public final LiveData<Boolean> isLoggedIn = _isLoggedIn;

    private final MutableLiveData<UserResponse> _userProfile = new MutableLiveData<>();
    public final LiveData<UserResponse> userProfile = _userProfile;

    private final MutableLiveData<Boolean> _isLoading = new MutableLiveData<>(false);
    public final LiveData<Boolean> isLoading = _isLoading;

    private final MutableLiveData<Integer> _errorMessageResId = new MutableLiveData<>();
    public final LiveData<Integer> errorMessageResId = _errorMessageResId;

    public MainViewModel(AuthManager authManager, SentinelApiService apiService) {
        this(authManager, apiService, null);
    }

    public MainViewModel(AuthManager authManager, SentinelApiService apiService, Context context) {
        this.authManager = authManager;
        this.apiService = apiService;
        this.localRepo = (context != null) ? LocalRepository.getInstance(context) : null;
        this.pipeline = new MentalHealthPipeline();
        if (context != null) {
            this.pipeline.initializeKnowledgeBase(context);
        }
        _isLoggedIn.setValue(authManager.isLoggedIn());
    }

    public MentalHealthPipeline getPipeline() {
        return pipeline;
    }

    public LocalRepository getLocalRepo() {
        return localRepo;
    }

    public void login(String email, String password) {
        _errorMessageResId.setValue(null);
        _isLoading.setValue(true);

        // Try online server authentication first
        apiService.login(new LoginRequest(email, password)).enqueue(new Callback<>() {
            @Override
            public void onResponse(@NonNull Call<TokenResponse> call, @NonNull Response<TokenResponse> response) {
                _isLoading.setValue(false);
                if (!response.isSuccessful() || response.body() == null) {
                    // Check local on-device credentials fallback
                    if (attemptOfflineLogin(email, password)) {
                        return;
                    }
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
                // Server unavailable: execute on-device offline login
                if (attemptOfflineLogin(email, password)) {
                    _isLoading.setValue(false);
                    return;
                }
                _isLoading.setValue(false);
                _errorMessageResId.setValue(R.string.error_connection);
            }
        });
    }

    private boolean attemptOfflineLogin(String email, String password) {
        if (localRepo != null) {
            UserResponse offlineUser = localRepo.authenticateOffline(email, password);
            if (offlineUser != null) {
                authManager.saveTokens("offline_token_" + System.currentTimeMillis(), "offline_refresh");
                _userProfile.setValue(offlineUser);
                _isLoggedIn.setValue(true);
                return true;
            }
        }
        return false;
    }

    public void loadProfile() {
        if (_userProfile.getValue() != null) {
            return;
        }

        if (localRepo != null) {
            List<UserResponse> offlineUsers = localRepo.getAllUsersOffline();
            if (!offlineUsers.isEmpty()) {
                _userProfile.setValue(offlineUsers.get(0));
                return;
            }
        }

        _isLoading.setValue(true);
        apiService.getUserProfile().enqueue(new Callback<>() {
            @Override
            public void onResponse(@NonNull Call<UserResponse> call, @NonNull Response<UserResponse> response) {
                _isLoading.setValue(false);
                if (!response.isSuccessful() || response.body() == null) {
                    logout();
                    _errorMessageResId.setValue(R.string.error_session_expired);
                    if (_userProfile.getValue() == null) {
                        logout();
                        _errorMessageResId.setValue(R.string.error_session_expired);
                    }
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
                // In offline mode, retain active user profile
                // In offline mode, retain active user profile or restore from local DB
                if (_userProfile.getValue() == null) {
                    if (localRepo != null) {
                        List<UserResponse> users = localRepo.getAllUsersOffline();
                        if (!users.isEmpty()) {
                            _userProfile.setValue(users.get(0));
                            return;
                        }
                    }
                    logout();
                    _errorMessageResId.setValue(R.string.error_load_profile);
                }
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

    /**
     * Executes AI Companion chat turn via the on-device HK Neural Composite Pipeline.
     */
    public void sendChat(String message, String conversationId, Callback<ChatResponse> callback) {
        apiService.sendChat(new ChatRequest(message, conversationId)).enqueue(callback);
        // Execute On-Device HK Neural Composite Pipeline
        PipelineContext ctx = pipeline.run(message);

        String responseText = (String) ctx.get("generated_text");
        Boolean isCrisis = (Boolean) ctx.get("is_crisis");
        Integer morale = (Integer) ctx.get("morale_score");
        String matchedProtocol = (String) ctx.get("matched_protocol");

        int finalMorale = (morale != null) ? morale : 50;
        boolean finalCrisis = Boolean.TRUE.equals(isCrisis);

        if (localRepo != null) {
            localRepo.logChatOffline("user", message, finalMorale, matchedProtocol);
            localRepo.logChatOffline("assistant", responseText, finalMorale, matchedProtocol);
        }

        ChatResponse localResponse = new ChatResponse(
                conversationId != null ? conversationId : "local-conv-" + System.currentTimeMillis(),
                responseText,
                finalCrisis
        );

        // Deliver immediate on-device result to UI
        if (callback != null) {
            callback.onResponse(null, Response.success(localResponse));
        }

        // Optional background sync if online
        try {
            apiService.sendChat(new ChatRequest(message, conversationId)).enqueue(new Callback<>() {
                @Override public void onResponse(@NonNull Call<ChatResponse> call, @NonNull Response<ChatResponse> response) {}
                @Override public void onFailure(@NonNull Call<ChatResponse> call, @NonNull Throwable t) {}
            });
        } catch (Exception ignored) {}
    }

    /**
     * Saves daily journal reflection to on-device SQLite database.
     */
    public void saveJournal(String content, String mood, String status, Callback<JournalResponse> callback) {
        apiService.createJournal(new JournalRequest(content, mood, status)).enqueue(callback);
        JournalResponse savedResponse = null;
        if (localRepo != null) {
            savedResponse = localRepo.saveJournalOffline(content, mood, status);
        } else {
            savedResponse = new JournalResponse("j-" + System.currentTimeMillis(), content, mood, status, "Just now");
        }

        // Deliver immediate on-device result to UI
        if (callback != null) {
            callback.onResponse(null, Response.success(savedResponse));
        }

        // Optional background sync if online
        try {
            apiService.createJournal(new JournalRequest(content, mood, status)).enqueue(new Callback<>() {
                @Override public void onResponse(@NonNull Call<JournalResponse> call, @NonNull Response<JournalResponse> response) {}
                @Override public void onFailure(@NonNull Call<JournalResponse> call, @NonNull Throwable t) {}
            });
        } catch (Exception ignored) {}
    }

    public List<JournalResponse> getSavedJournals() {
        if (localRepo != null) {
            return localRepo.getJournalsOffline();
        }
        return new java.util.ArrayList<>();
    }

    public static class Factory implements ViewModelProvider.Factory {
        private final AuthManager authManager;
        private final SentinelApiService apiService;
        private final Context context;

        public Factory(AuthManager authManager, SentinelApiService apiService) {
            this(authManager, apiService, null);
        }

        public Factory(AuthManager authManager, SentinelApiService apiService, Context context) {
            this.authManager = authManager;
            this.apiService = apiService;
            this.context = context != null ? context.getApplicationContext() : null;
        }

        @NonNull
        @Override
        public <T extends ViewModel> T create(@NonNull Class<T> modelClass) {
            if (modelClass.isAssignableFrom(MainViewModel.class)) {
                return (T) new MainViewModel(authManager, apiService, context);
            }
            throw new IllegalArgumentException("Unknown ViewModel class");
        }
    }
}
