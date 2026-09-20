package com.example.myapplication.sync;

import android.content.Context;

import androidx.annotation.NonNull;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import com.example.myapplication.api.ApiClient;
import com.example.myapplication.api.SentinelApiService;
import com.example.myapplication.auth.AuthManager;
import com.example.myapplication.data.LocalRepository;
import com.example.myapplication.models.JournalRequest;
import com.example.myapplication.models.JournalResponse;

import java.io.IOException;
import java.util.List;

import okhttp3.ResponseBody;
import retrofit2.Response;

public class JournalSyncWorker extends Worker {
    private static final int SYNC_BATCH_SIZE = 20;

    public JournalSyncWorker(@NonNull Context appContext, @NonNull WorkerParameters workerParams) {
        super(appContext, workerParams);
    }

    @NonNull
    @Override
    public Result doWork() {
        Context appContext = getApplicationContext();
        LocalRepository repository = LocalRepository.getInstance(appContext);
        if (repository == null || repository.countJournalsAwaitingSync() == 0) {
            JournalSyncMonitor.post(JournalSyncStatus.SYNCED);
            return Result.success();
        }

        AuthManager authManager = new AuthManager(appContext);
        if (!authManager.hasCloudSession()) {
            JournalSyncMonitor.post(JournalSyncStatus.SAVED_OFFLINE);
            return Result.success();
        }

        JournalSyncMonitor.post(JournalSyncStatus.SYNCING);
        SentinelApiService apiService = ApiClient.getClient(appContext, authManager)
                .create(SentinelApiService.class);
        List<LocalRepository.PendingJournal> pending =
                repository.getJournalsAwaitingSync(SYNC_BATCH_SIZE);
        boolean hasPermanentFailure = false;

        for (LocalRepository.PendingJournal journal : pending) {
            if (isStopped()) {
                JournalSyncMonitor.post(JournalSyncStatus.SAVED_OFFLINE);
                return Result.retry();
            }

            repository.markJournalSyncing(journal.getLocalId());
            JournalRequest request = new JournalRequest(
                    journal.getContent(),
                    journal.getMood(),
                    journal.getStatus(),
                    journal.getClientRequestId()
            );

            try {
                Response<JournalResponse> response = apiService.createJournal(request).execute();
                try {
                    if (response.isSuccessful() || response.code() == 409) {
                        JournalResponse body = response.body();
                        repository.markJournalSynced(
                                journal.getLocalId(),
                                body != null ? body.getId() : null
                        );
                        continue;
                    }

                    int code = response.code();
                    repository.markJournalPendingAfterFailure(
                            journal.getLocalId(),
                            "HTTP " + code
                    );
                    if (isTransient(code)) {
                        JournalSyncMonitor.post(JournalSyncStatus.SAVED_OFFLINE);
                        return Result.retry();
                    }
                    if (code == 401 || code == 403) {
                        JournalSyncMonitor.post(JournalSyncStatus.SAVED_OFFLINE);
                        return Result.failure();
                    }
                    hasPermanentFailure = true;
                } finally {
                    ResponseBody errorBody = response.errorBody();
                    if (errorBody != null) {
                        errorBody.close();
                    }
                }
            } catch (IOException | RuntimeException exception) {
                repository.markJournalPendingAfterFailure(journal.getLocalId(), "Network unavailable");
                JournalSyncMonitor.post(JournalSyncStatus.SAVED_OFFLINE);
                return Result.retry();
            }
        }

        int remaining = repository.countJournalsAwaitingSync();
        if (remaining == 0) {
            JournalSyncMonitor.post(JournalSyncStatus.SYNCED);
            return Result.success();
        }

        JournalSyncMonitor.post(JournalSyncStatus.SAVED_OFFLINE);
        return hasPermanentFailure ? Result.failure() : Result.retry();
    }

    private static boolean isTransient(int code) {
        return code == 408 || code == 425 || code == 429 || code >= 500;
    }
}
