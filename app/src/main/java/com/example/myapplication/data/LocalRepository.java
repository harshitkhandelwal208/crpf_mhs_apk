package com.example.myapplication.data;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;

import com.example.myapplication.models.JournalResponse;
import com.example.myapplication.models.UserResponse;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.TimeZone;
import java.util.UUID;

/**
 * Local, app-scoped persistence for offline demo authentication, cached profile data,
 * journal delivery state, and a bounded on-device chat history.
 */
public class LocalRepository extends SQLiteOpenHelper {
    private static final String DATABASE_NAME = "crpf_sentinel_local.db";
    private static final int DATABASE_VERSION = 2;

    private static final String TABLE_USERS = "local_users";
    private static final String TABLE_ACTIVE_PROFILE = "active_profile";
    private static final String TABLE_JOURNALS = "local_journals";
    private static final String TABLE_CHATS = "local_chats";

    private static final String DEMO_EMAIL_ONE = "personnel1@sentinel.mil";
    private static final String DEMO_EMAIL_TWO = "rajesh.kumar@crpf.gov.in";
    private static final int MAX_CHAT_HISTORY = 200;
    private static final int MAX_SYNCED_JOURNAL_HISTORY = 365;

    public static final String SYNC_STATE_PENDING = "PENDING";
    public static final String SYNC_STATE_SYNCING = "SYNCING";
    public static final String SYNC_STATE_SYNCED = "SYNCED";

    private static LocalRepository instance;

    public static synchronized LocalRepository getInstance(Context context) {
        if (instance == null && context != null) {
            instance = new LocalRepository(context.getApplicationContext());
        }
        return instance;
    }

    public LocalRepository(Context context) {
        super(context, DATABASE_NAME, null, DATABASE_VERSION);
        setWriteAheadLoggingEnabled(true);
    }

    @Override
    public void onCreate(SQLiteDatabase db) {
        db.execSQL("CREATE TABLE " + TABLE_USERS + " (" +
                "id TEXT PRIMARY KEY, " +
                "email TEXT UNIQUE NOT NULL, " +
                "password TEXT, " +
                "full_name TEXT NOT NULL, " +
                "role TEXT NOT NULL, " +
                "service_number TEXT)");

        createActiveProfileTable(db);

        db.execSQL("CREATE TABLE " + TABLE_JOURNALS + " (" +
                "id TEXT PRIMARY KEY, " +
                "content TEXT NOT NULL, " +
                "mood TEXT, " +
                "status TEXT, " +
                "created_at TEXT NOT NULL, " +
                "client_request_id TEXT NOT NULL, " +
                "sync_state TEXT NOT NULL DEFAULT '" + SYNC_STATE_PENDING + "', " +
                "server_id TEXT, " +
                "last_sync_error TEXT, " +
                "last_sync_attempt_at TEXT)");
        createJournalIndexes(db);

        db.execSQL("CREATE TABLE " + TABLE_CHATS + " (" +
                "id TEXT PRIMARY KEY, " +
                "sender TEXT NOT NULL, " +
                "message TEXT NOT NULL, " +
                "morale_score INTEGER, " +
                "matched_protocol TEXT, " +
                "created_at TEXT NOT NULL)");

        seedDemoUsers(db);
    }

    @Override
    public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {
        if (oldVersion < 2) {
            createActiveProfileTable(db);
            db.execSQL("ALTER TABLE " + TABLE_JOURNALS + " ADD COLUMN client_request_id TEXT");
            db.execSQL("ALTER TABLE " + TABLE_JOURNALS + " ADD COLUMN sync_state TEXT NOT NULL DEFAULT '" + SYNC_STATE_PENDING + "'");
            db.execSQL("ALTER TABLE " + TABLE_JOURNALS + " ADD COLUMN server_id TEXT");
            db.execSQL("ALTER TABLE " + TABLE_JOURNALS + " ADD COLUMN last_sync_error TEXT");
            db.execSQL("ALTER TABLE " + TABLE_JOURNALS + " ADD COLUMN last_sync_attempt_at TEXT");
            db.execSQL("UPDATE " + TABLE_JOURNALS + " SET client_request_id = id WHERE client_request_id IS NULL");
            createJournalIndexes(db);

            // v1 could create arbitrary local accounts containing supplied plaintext
            // passwords. Keep only the two explicit demo fallback accounts.
            db.delete(
                    TABLE_USERS,
                    "LOWER(email) NOT IN (?, ?)",
                    new String[]{DEMO_EMAIL_ONE, DEMO_EMAIL_TWO}
            );
        }
    }

    /**
     * Authenticates only the explicitly seeded demo accounts. Unknown credentials
     * are never persisted or promoted to a local account.
     */
    public UserResponse authenticateOffline(String email, String password) {
        if (email == null || password == null) {
            return null;
        }

        UserResponse user = null;
        SQLiteDatabase db = getReadableDatabase();
        try (Cursor cursor = db.query(
                TABLE_USERS,
                new String[]{"id", "email", "full_name", "role"},
                "LOWER(email) = ? AND password = ?",
                new String[]{email.toLowerCase(Locale.US).trim(), password},
                null,
                null,
                null,
                "1"
        )) {
            if (cursor.moveToFirst()) {
                user = userFromCursor(cursor);
            }
        }

        if (user != null) {
            saveActiveProfile(user);
        }
        return user;
    }

    public List<UserResponse> getAllUsersOffline() {
        List<UserResponse> users = new ArrayList<>();
        SQLiteDatabase db = getReadableDatabase();
        try (Cursor cursor = db.query(
                TABLE_USERS,
                new String[]{"id", "email", "full_name", "role"},
                null,
                null,
                null,
                null,
                "full_name ASC"
        )) {
            while (cursor.moveToNext()) {
                users.add(userFromCursor(cursor));
            }
        }
        return users;
    }

    public void saveActiveProfile(UserResponse user) {
        if (user == null || user.getId() == null || user.getEmail() == null) {
            return;
        }
        ContentValues values = new ContentValues();
        values.put("singleton_id", 1);
        values.put("user_id", user.getId());
        values.put("email", user.getEmail());
        values.put("full_name", user.getFullName() != null ? user.getFullName() : "Personnel member");
        values.put("role", user.getRole() != null ? user.getRole() : "PERSONNEL");
        values.put("updated_at", now());
        getWritableDatabase().insertWithOnConflict(
                TABLE_ACTIVE_PROFILE,
                null,
                values,
                SQLiteDatabase.CONFLICT_REPLACE
        );
    }

    public UserResponse getActiveProfile() {
        SQLiteDatabase db = getReadableDatabase();
        try (Cursor cursor = db.query(
                TABLE_ACTIVE_PROFILE,
                new String[]{"user_id", "email", "full_name", "role"},
                "singleton_id = 1",
                null,
                null,
                null,
                null,
                "1"
        )) {
            if (!cursor.moveToFirst()) {
                return null;
            }
            return new UserResponse(
                    cursor.getString(cursor.getColumnIndexOrThrow("user_id")),
                    cursor.getString(cursor.getColumnIndexOrThrow("email")),
                    cursor.getString(cursor.getColumnIndexOrThrow("full_name")),
                    cursor.getString(cursor.getColumnIndexOrThrow("role"))
            );
        }
    }

    public void clearActiveProfile() {
        getWritableDatabase().delete(TABLE_ACTIVE_PROFILE, "singleton_id = 1", null);
    }

    /** Saves one journal entry locally as pending and assigns its stable idempotency ID. */
    public JournalResponse saveJournalPending(String content, String mood, String status) {
        SQLiteDatabase db = getWritableDatabase();
        String id = UUID.randomUUID().toString();
        String createdAt = now();

        ContentValues values = new ContentValues();
        values.put("id", id);
        values.put("content", content);
        values.put("mood", mood != null ? mood : "steady");
        values.put("status", status != null ? status : "SUBMITTED");
        values.put("created_at", createdAt);
        values.put("client_request_id", id);
        values.put("sync_state", SYNC_STATE_PENDING);

        db.beginTransaction();
        try {
            db.insertOrThrow(TABLE_JOURNALS, null, values);
            pruneSyncedJournals(db);
            db.setTransactionSuccessful();
        } finally {
            db.endTransaction();
        }
        return new JournalResponse(id, content, mood, status, createdAt);
    }

    public List<JournalResponse> getJournalsOffline() {
        List<JournalResponse> journals = new ArrayList<>();
        SQLiteDatabase db = getReadableDatabase();
        try (Cursor cursor = db.query(
                TABLE_JOURNALS,
                new String[]{"id", "content", "mood", "status", "created_at"},
                null,
                null,
                null,
                null,
                "created_at DESC, rowid DESC",
                String.valueOf(MAX_SYNCED_JOURNAL_HISTORY)
        )) {
            while (cursor.moveToNext()) {
                journals.add(new JournalResponse(
                        cursor.getString(cursor.getColumnIndexOrThrow("id")),
                        cursor.getString(cursor.getColumnIndexOrThrow("content")),
                        cursor.getString(cursor.getColumnIndexOrThrow("mood")),
                        cursor.getString(cursor.getColumnIndexOrThrow("status")),
                        cursor.getString(cursor.getColumnIndexOrThrow("created_at"))
                ));
            }
        }
        return journals;
    }

    public List<PendingJournal> getJournalsAwaitingSync(int limit) {
        List<PendingJournal> journals = new ArrayList<>();
        SQLiteDatabase db = getReadableDatabase();
        try (Cursor cursor = db.query(
                TABLE_JOURNALS,
                new String[]{"id", "content", "mood", "status", "client_request_id"},
                "sync_state != ?",
                new String[]{SYNC_STATE_SYNCED},
                null,
                null,
                "created_at ASC, rowid ASC",
                String.valueOf(limit)
        )) {
            while (cursor.moveToNext()) {
                journals.add(new PendingJournal(
                        cursor.getString(cursor.getColumnIndexOrThrow("id")),
                        cursor.getString(cursor.getColumnIndexOrThrow("content")),
                        cursor.getString(cursor.getColumnIndexOrThrow("mood")),
                        cursor.getString(cursor.getColumnIndexOrThrow("status")),
                        cursor.getString(cursor.getColumnIndexOrThrow("client_request_id"))
                ));
            }
        }
        return journals;
    }

    public int countJournalsAwaitingSync() {
        SQLiteDatabase db = getReadableDatabase();
        try (Cursor cursor = db.rawQuery(
                "SELECT COUNT(*) FROM " + TABLE_JOURNALS + " WHERE sync_state != ?",
                new String[]{SYNC_STATE_SYNCED}
        )) {
            return cursor.moveToFirst() ? cursor.getInt(0) : 0;
        }
    }

    public void markJournalSyncing(String localId) {
        ContentValues values = new ContentValues();
        values.put("sync_state", SYNC_STATE_SYNCING);
        values.put("last_sync_attempt_at", now());
        values.putNull("last_sync_error");
        getWritableDatabase().update(
                TABLE_JOURNALS,
                values,
                "id = ? AND sync_state != ?",
                new String[]{localId, SYNC_STATE_SYNCED}
        );
    }

    public void markJournalSynced(String localId, String serverId) {
        SQLiteDatabase db = getWritableDatabase();
        ContentValues values = new ContentValues();
        values.put("sync_state", SYNC_STATE_SYNCED);
        if (serverId != null && !serverId.trim().isEmpty()) {
            values.put("server_id", serverId);
        }
        values.putNull("last_sync_error");
        db.beginTransaction();
        try {
            db.update(TABLE_JOURNALS, values, "id = ?", new String[]{localId});
            pruneSyncedJournals(db);
            db.setTransactionSuccessful();
        } finally {
            db.endTransaction();
        }
    }

    public void markJournalPendingAfterFailure(String localId, String error) {
        ContentValues values = new ContentValues();
        values.put("sync_state", SYNC_STATE_PENDING);
        values.put("last_sync_error", error);
        getWritableDatabase().update(TABLE_JOURNALS, values, "id = ?", new String[]{localId});
    }

    public void logChatOffline(String sender, String message, int moraleScore, String matchedProtocol) {
        SQLiteDatabase db = getWritableDatabase();
        ContentValues values = new ContentValues();
        values.put("id", UUID.randomUUID().toString());
        values.put("sender", sender);
        values.put("message", message);
        values.put("morale_score", moraleScore);
        values.put("matched_protocol", matchedProtocol);
        values.put("created_at", now());

        db.beginTransaction();
        try {
            db.insertOrThrow(TABLE_CHATS, null, values);
            db.execSQL("DELETE FROM " + TABLE_CHATS + " WHERE rowid IN (" +
                    "SELECT rowid FROM " + TABLE_CHATS +
                    " ORDER BY created_at DESC, rowid DESC LIMIT -1 OFFSET " + MAX_CHAT_HISTORY + ")");
            db.setTransactionSuccessful();
        } finally {
            db.endTransaction();
        }
    }

    private static void createActiveProfileTable(SQLiteDatabase db) {
        db.execSQL("CREATE TABLE IF NOT EXISTS " + TABLE_ACTIVE_PROFILE + " (" +
                "singleton_id INTEGER PRIMARY KEY CHECK(singleton_id = 1), " +
                "user_id TEXT NOT NULL, " +
                "email TEXT NOT NULL, " +
                "full_name TEXT NOT NULL, " +
                "role TEXT NOT NULL, " +
                "updated_at TEXT NOT NULL)");
    }

    private static void createJournalIndexes(SQLiteDatabase db) {
        db.execSQL("CREATE UNIQUE INDEX IF NOT EXISTS idx_journal_client_request " +
                "ON " + TABLE_JOURNALS + "(client_request_id)");
        db.execSQL("CREATE INDEX IF NOT EXISTS idx_journal_sync_state " +
                "ON " + TABLE_JOURNALS + "(sync_state, created_at)");
    }

    private static void seedDemoUsers(SQLiteDatabase db) {
        insertDemoUser(
                db,
                DEMO_EMAIL_ONE,
                "sentinel-pers-2024",
                "Sgt. Mike Johnson",
                "CRPF-84920"
        );
        insertDemoUser(
                db,
                DEMO_EMAIL_TWO,
                "password123",
                "Constable Rajesh Kumar",
                "CRPF-91042"
        );
    }

    private static void insertDemoUser(
            SQLiteDatabase db,
            String email,
            String password,
            String fullName,
            String serviceNumber
    ) {
        ContentValues values = new ContentValues();
        values.put("id", UUID.randomUUID().toString());
        values.put("email", email);
        values.put("password", password);
        values.put("full_name", fullName);
        values.put("role", "PERSONNEL");
        values.put("service_number", serviceNumber);
        db.insertWithOnConflict(TABLE_USERS, null, values, SQLiteDatabase.CONFLICT_IGNORE);
    }

    private static UserResponse userFromCursor(Cursor cursor) {
        UserResponse user = new UserResponse();
        user.setId(cursor.getString(cursor.getColumnIndexOrThrow("id")));
        user.setEmail(cursor.getString(cursor.getColumnIndexOrThrow("email")));
        user.setFullName(cursor.getString(cursor.getColumnIndexOrThrow("full_name")));
        user.setRole(cursor.getString(cursor.getColumnIndexOrThrow("role")));
        return user;
    }

    private static void pruneSyncedJournals(SQLiteDatabase db) {
        db.execSQL("DELETE FROM " + TABLE_JOURNALS + " WHERE rowid IN (" +
                "SELECT rowid FROM " + TABLE_JOURNALS +
                " WHERE sync_state = '" + SYNC_STATE_SYNCED + "'" +
                " ORDER BY created_at DESC, rowid DESC LIMIT -1 OFFSET " + MAX_SYNCED_JOURNAL_HISTORY + ")");
    }

    private static String now() {
        SimpleDateFormat format = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", Locale.US);
        format.setTimeZone(TimeZone.getTimeZone("UTC"));
        return format.format(new Date());
    }

    public static final class PendingJournal {
        private final String localId;
        private final String content;
        private final String mood;
        private final String status;
        private final String clientRequestId;

        PendingJournal(String localId, String content, String mood, String status, String clientRequestId) {
            this.localId = localId;
            this.content = content;
            this.mood = mood;
            this.status = status;
            this.clientRequestId = clientRequestId;
        }

        public String getLocalId() {
            return localId;
        }

        public String getContent() {
            return content;
        }

        public String getMood() {
            return mood;
        }

        public String getStatus() {
            return status;
        }

        public String getClientRequestId() {
            return clientRequestId;
        }
    }
}
