package com.example.myapplication;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;

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
import com.example.myapplication.models.ChatRequest;
import com.example.myapplication.models.ChatResponse;
import com.example.myapplication.models.JournalResponse;
import com.example.myapplication.models.LoginRequest;
import com.example.myapplication.models.TokenResponse;
import com.example.myapplication.models.UserResponse;
import com.example.myapplication.sync.JournalSyncMonitor;
import com.example.myapplication.sync.JournalSyncScheduler;
import com.example.myapplication.sync.JournalSyncStatus;

import java.util.Collections;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

/**
 * App state and local-first operations for the CRPF MHS mobile client.
 */
public class MainViewModel extends ViewModel {
    private static final String PERSONNEL_ROLE = "PERSONNEL";

    private static final Callback<ChatResponse> NO_OP_CHAT_SYNC_CALLBACK = new Callback<>() {
        @Override
        public void onResponse(@NonNull Call<ChatResponse> call, @NonNull Response<ChatResponse> response) {
            // The on-device response is authoritative for this UI turn.
        }

        @Override
        public void onFailure(@NonNull Call<ChatResponse> call, @NonNull Throwable throwable) {
            // Chat cloud sync is best-effort; never replace the local response.
        }
    };

    private final AuthManager authManager;
    private final SentinelApiService apiService;
    private final LocalRepository localRepo;
    private final MentalHealthPipeline pipeline;
    private final Context appContext;
    private final ExecutorService localExecutor = Executors.newSingleThreadExecutor();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());

    private volatile Call<TokenResponse> loginCall;
    private volatile Call<UserResponse> profileCall;

    private final MutableLiveData<Boolean> _isLoggedIn = new MutableLiveData<>();
    public final LiveData<Boolean> isLoggedIn = _isLoggedIn;

    private final MutableLiveData<UserResponse> _userProfile = new MutableLiveData<>();
    public final LiveData<UserResponse> userProfile = _userProfile;

    private final MutableLiveData<Boolean> _isLoading = new MutableLiveData<>(false);
    public final LiveData<Boolean> isLoading = _isLoading;

    private final MutableLiveData<Integer> _errorMessageResId = new MutableLiveData<>();
    public final LiveData<Integer> errorMessageResId = _errorMessageResId;

    public final LiveData<JournalSyncStatus> journalSyncStatus = JournalSyncMonitor.status();

    public MainViewModel(AuthManager authManager, SentinelApiService apiService) {
        this(authManager, apiService, null);
    }

    public MainViewModel(AuthManager authManager, SentinelApiService apiService, Context context) {
        this.authManager = authManager;
        this.apiService = apiService;
        this.appContext = context != null ? context.getApplicationContext() : null;
        this.localRepo = appContext != null ? LocalRepository.getInstance(appContext) : null;
        this.pipeline = new MentalHealthPipeline();
        _isLoggedIn.setValue(authManager.isLoggedIn());

        if (appContext != null) {
            localExecutor.execute(() -> {
                pipeline.initializeKnowledgeBase(appContext);
                refreshJournalSyncStatus();
            });
        }
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

        Call<TokenResponse> call = apiService.login(new LoginRequest(email, password));
        loginCall = call;
        call.enqueue(new Callback<>() {
            @Override
            public void onResponse(@NonNull Call<TokenResponse> call, @NonNull Response<TokenResponse> response) {
                TokenResponse tokens = response.body();
                if (!response.isSuccessful()
                        || tokens == null
                        || tokens.getAccessToken() == null
                        || tokens.getAccessToken().trim().isEmpty()) {
                    attemptOfflineLogin(
                            email,
                            password,
                            response.code() == 401
                                    ? R.string.error_invalid_credentials
                                    : R.string.error_generic_login
                    );
                    return;
                }

                authManager.saveTokens(tokens.getAccessToken(), tokens.getRefreshToken());
                if (localRepo != null) {
                    localRepo.clearActiveProfile();
                }
                _userProfile.setValue(null);
                _isLoggedIn.setValue(true);
                if (appContext != null) {
                    JournalSyncScheduler.enqueue(appContext);
                }
                loadProfileFromNetwork(false);
            }

            @Override
            public void onFailure(@NonNull Call<TokenResponse> call, @NonNull Throwable throwable) {
                attemptOfflineLogin(email, password, R.string.error_connection);
            }
        });
    }

    private void attemptOfflineLogin(String email, String password, int failureMessage) {
        if (localRepo == null) {
            _isLoading.setValue(false);
            _errorMessageResId.setValue(failureMessage);
            return;
        }

        localExecutor.execute(() -> {
            UserResponse offlineUser = localRepo.authenticateOffline(email, password);
            mainHandler.post(() -> {
                _isLoading.setValue(false);
                if (offlineUser == null) {
                    _errorMessageResId.setValue(failureMessage);
                    return;
                }
                authManager.saveOfflineSession();
                _userProfile.setValue(offlineUser);
                _isLoggedIn.setValue(true);
            });
        });
    }

    public void loadProfile() {
        UserResponse cachedProfile = localRepo != null ? localRepo.getActiveProfile() : null;
        if (cachedProfile != null) {
            _userProfile.setValue(cachedProfile);
        }
        if (!authManager.hasCloudSession()) {
            _isLoading.setValue(false);
            return;
        }
        loadProfileFromNetwork(cachedProfile != null);
    }

    private void loadProfileFromNetwork(boolean hasCachedProfile) {
        if (!hasCachedProfile) {
            _isLoading.setValue(true);
        }
        Call<UserResponse> call = apiService.getUserProfile();
        profileCall = call;
        call.enqueue(new Callback<>() {
            @Override
            public void onResponse(@NonNull Call<UserResponse> call, @NonNull Response<UserResponse> response) {
                _isLoading.setValue(false);
                UserResponse user = response.body();
                if (!response.isSuccessful() || user == null) {
                    if (response.code() == 401 || response.code() == 403) {
                        logout();
                        _errorMessageResId.setValue(R.string.error_session_expired);
                    } else if (!hasCachedProfile) {
                        _errorMessageResId.setValue(R.string.error_load_profile);
                    }
                    return;
                }
                if (!PERSONNEL_ROLE.equals(user.getRole())) {
                    logout();
                    _errorMessageResId.setValue(R.string.error_personnel_only);
                    return;
                }

                if (localRepo != null) {
                    localRepo.saveActiveProfile(user);
                }
                _userProfile.setValue(user);
            }

            @Override
            public void onFailure(@NonNull Call<UserResponse> call, @NonNull Throwable throwable) {
                _isLoading.setValue(false);
                if (!hasCachedProfile && _userProfile.getValue() == null) {
                    _errorMessageResId.setValue(R.string.error_load_profile);
                }
            }
        });
    }

    public void logout() {
        authManager.clearTokens();
        if (localRepo != null) {
            localRepo.clearActiveProfile();
        }
        _isLoggedIn.setValue(false);
        _userProfile.setValue(null);
    }

    public void clearError() {
        _errorMessageResId.setValue(null);
    }

    /**
     * Runs one local chat turn away from the main thread, returns exactly one local
     * result, and submits one best-effort cloud copy for authenticated cloud sessions.
     */
    public void sendChat(String message, String conversationId, LocalResultCallback<ChatResponse> callback) {
        localExecutor.execute(() -> {
            try {
                PipelineContext context = pipeline.run(message);
                String responseText = context.getString(
                        "generated_text",
                        "I am here with you. Please try sharing that again, or contact your support team if you need a person now."
                );
                int morale = context.getInt("morale_score", 50);
                boolean isCrisis = context.getBoolean("is_crisis", false);
                String matchedProtocol = context.getString("matched_protocol", null);

                if (localRepo != null) {
                    try {
                        localRepo.logChatOffline("user", message, morale, matchedProtocol);
                        localRepo.logChatOffline("assistant", responseText, morale, matchedProtocol);
                    } catch (RuntimeException ignored) {
                        // A storage issue must not suppress an otherwise valid local response.
                    }
                }

                ChatResponse localResponse = new ChatResponse(
                        conversationId != null
                                ? conversationId
                                : "local-conv-" + System.currentTimeMillis(),
                        responseText,
                        isCrisis
                );
                mainHandler.post(() -> callback.onSuccess(localResponse));
            } catch (RuntimeException exception) {
                mainHandler.post(() -> callback.onError(exception));
            } finally {
                syncChatOnce(message, conversationId);
            }
        });
    }

    private void syncChatOnce(String message, String conversationId) {
        if (!authManager.hasCloudSession()) {
            return;
        }
        try {
            apiService.sendChat(new ChatRequest(message, conversationId))
                    .enqueue(NO_OP_CHAT_SYNC_CALLBACK);
        } catch (RuntimeException ignored) {
            // The local result remains available if a request cannot be enqueued.
        }
    }

    /** Saves once locally and delegates the only cloud path to unique WorkManager work. */
    public void saveJournal(
            String content,
            String mood,
            String status,
            LocalResultCallback<JournalResponse> callback
    ) {
        localExecutor.execute(() -> {
            try {
                if (localRepo == null || appContext == null) {
                    throw new IllegalStateException("Local journal storage is unavailable");
                }
                JournalResponse saved = localRepo.saveJournalPending(content, mood, status);
                JournalSyncMonitor.post(JournalSyncStatus.SAVED_OFFLINE);
                JournalSyncScheduler.enqueue(appContext);
                mainHandler.post(() -> callback.onSuccess(saved));
            } catch (RuntimeException exception) {
                mainHandler.post(() -> callback.onError(exception));
            }
        });
    }

    public List<JournalResponse> getSavedJournals() {
        return localRepo != null ? localRepo.getJournalsOffline() : Collections.emptyList();
    }

    private void refreshJournalSyncStatus() {
        if (localRepo == null || localRepo.countJournalsAwaitingSync() == 0) {
            JournalSyncMonitor.post(JournalSyncStatus.SYNCED);
        } else {
            JournalSyncMonitor.post(JournalSyncStatus.SAVED_OFFLINE);
        }
    }

    @Override
    protected void onCleared() {
        Call<TokenResponse> currentLoginCall = loginCall;
        if (currentLoginCall != null) {
            currentLoginCall.cancel();
        }
        Call<UserResponse> currentProfileCall = profileCall;
        if (currentProfileCall != null) {
            currentProfileCall.cancel();
        }
        localExecutor.shutdownNow();
        super.onCleared();
    }

    public interface LocalResultCallback<T> {
        void onSuccess(T result);

        void onError(Throwable throwable);
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
        @SuppressWarnings("unchecked")
        public <T extends ViewModel> T create(@NonNull Class<T> modelClass) {
            if (modelClass.isAssignableFrom(MainViewModel.class)) {
                return (T) new MainViewModel(authManager, apiService, context);
            }
            throw new IllegalArgumentException("Unknown ViewModel class");
        }
    }
}
