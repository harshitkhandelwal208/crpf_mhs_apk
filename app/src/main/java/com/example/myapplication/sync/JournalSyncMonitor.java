package com.example.myapplication.sync;

import androidx.lifecycle.LiveData;
import androidx.lifecycle.MutableLiveData;

public final class JournalSyncMonitor {
    private static final MutableLiveData<JournalSyncStatus> STATUS =
            new MutableLiveData<>(JournalSyncStatus.SYNCED);

    private JournalSyncMonitor() {
    }

    public static LiveData<JournalSyncStatus> status() {
        return STATUS;
    }

    public static void post(JournalSyncStatus status) {
        STATUS.postValue(status);
    }
}
