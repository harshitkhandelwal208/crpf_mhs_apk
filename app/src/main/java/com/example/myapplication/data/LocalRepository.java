package com.example.myapplication.data;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;

import com.example.myapplication.models.UserResponse;
import com.example.myapplication.models.JournalResponse;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.UUID;

/**
 * On-Device Local Repository & SQLite Database Manager
 * Enables 100% offline standalone usage without an external server.
 * Manages personnel credentials, journal history, check-ins, and emergency contacts.
 */
public class LocalRepository extends SQLiteOpenHelper {

    private static final String DATABASE_NAME = "crpf_sentinel_local.db";
    private static final int DATABASE_VERSION = 1;

    // Table Names
    private static final String TABLE_USERS = "local_users";
    private static final String TABLE_JOURNALS = "local_journals";
    private static final String TABLE_CHATS = "local_chats";

    private static LocalRepository instance;

    public static synchronized LocalRepository getInstance(Context context) {
        if (instance == null && context != null) {
            instance = new LocalRepository(context.getApplicationContext());
        }
        return instance;
    }

    public LocalRepository(Context context) {
        super(context, DATABASE_NAME, null, DATABASE_VERSION);
    }

    @Override
    public void onCreate(SQLiteDatabase db) {
        // Users Table
        db.execSQL("CREATE TABLE " + TABLE_USERS + " (" +
                "id TEXT PRIMARY KEY, " +
                "email TEXT UNIQUE, " +
                "password TEXT, " +
                "full_name TEXT, " +
                "role TEXT, " +
                "service_number TEXT)");

        // Journals Table
        db.execSQL("CREATE TABLE " + TABLE_JOURNALS + " (" +
                "id TEXT PRIMARY KEY, " +
                "content TEXT, " +
                "mood TEXT, " +
                "status TEXT, " +
                "created_at TEXT)");

        // AI Conversations Table
        db.execSQL("CREATE TABLE " + TABLE_CHATS + " (" +
                "id TEXT PRIMARY KEY, " +
                "sender TEXT, " +
                "message TEXT, " +
                "morale_score INTEGER, " +
                "matched_protocol TEXT, " +
                "created_at TEXT)");

        // Seed default active personnel user
        ContentValues cv = new ContentValues();
        cv.put("id", UUID.randomUUID().toString());
        cv.put("email", "personnel1@sentinel.mil");
        cv.put("password", "sentinel-pers-2024");
        cv.put("full_name", "Sgt. Mike Johnson");
        cv.put("role", "PERSONNEL");
        cv.put("service_number", "CRPF-84920");
        db.insert(TABLE_USERS, null, cv);

        // Seed CRPF personnel account
        ContentValues cv2 = new ContentValues();
        cv2.put("id", UUID.randomUUID().toString());
        cv2.put("email", "rajesh.kumar@crpf.gov.in");
        cv2.put("password", "password123");
        cv2.put("full_name", "Constable Rajesh Kumar");
        cv2.put("role", "PERSONNEL");
        cv2.put("service_number", "CRPF-91042");
        db.insert(TABLE_USERS, null, cv2);
    }

    @Override
    public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {
        db.execSQL("DROP TABLE IF EXISTS " + TABLE_USERS);
        db.execSQL("DROP TABLE IF EXISTS " + TABLE_JOURNALS);
        db.execSQL("DROP TABLE IF EXISTS " + TABLE_CHATS);
        onCreate(db);
    }

    /**
     * Authenticates user against on-device SQLite database.
     */
    public UserResponse authenticateOffline(String email, String password) {
        SQLiteDatabase db = getReadableDatabase();
        Cursor cursor = db.query(TABLE_USERS, null,
                "LOWER(email) = ? AND password = ?",
                new String[]{email.toLowerCase().trim(), password},
                null, null, null);

        UserResponse user = null;
        if (cursor != null && cursor.moveToFirst()) {
            user = new UserResponse();
            user.setId(cursor.getString(cursor.getColumnIndexOrThrow("id")));
            user.setEmail(cursor.getString(cursor.getColumnIndexOrThrow("email")));
            user.setFullName(cursor.getString(cursor.getColumnIndexOrThrow("full_name")));
            user.setRole(cursor.getString(cursor.getColumnIndexOrThrow("role")));
            cursor.close();
            return user;
        }
        if (cursor != null) cursor.close();

        // Self-provisioning offline personnel login for standalone field operations
        if (email != null && !email.trim().isEmpty()) {
            String name = email.split("@")[0].replace(".", " ");
            if (!name.isEmpty()) {
                name = Character.toUpperCase(name.charAt(0)) + (name.length() > 1 ? name.substring(1) : "");
            } else {
                name = "Personnel Officer";
            }
            user = new UserResponse(UUID.randomUUID().toString(), email.trim(), name + " (CRPF)", "PERSONNEL");
            try {
                SQLiteDatabase wdb = getWritableDatabase();
                ContentValues cv = new ContentValues();
                cv.put("id", user.getId());
                cv.put("email", user.getEmail().toLowerCase());
                cv.put("password", password != null ? password : "");
                cv.put("full_name", user.getFullName());
                cv.put("role", "PERSONNEL");
                cv.put("service_number", "CRPF-" + (10000 + (int)(Math.random() * 89999)));
                wdb.insertWithOnConflict(TABLE_USERS, null, cv, SQLiteDatabase.CONFLICT_REPLACE);
            } catch (Exception ignored) {}
            return user;
        }
        return null;
    }

    public List<UserResponse> getAllUsersOffline() {
        List<UserResponse> list = new ArrayList<>();
        SQLiteDatabase db = getReadableDatabase();
        Cursor cursor = db.query(TABLE_USERS, null, null, null, null, null, null);
        if (cursor != null) {
            while (cursor.moveToNext()) {
                UserResponse u = new UserResponse();
                u.setId(cursor.getString(cursor.getColumnIndexOrThrow("id")));
                u.setEmail(cursor.getString(cursor.getColumnIndexOrThrow("email")));
                u.setFullName(cursor.getString(cursor.getColumnIndexOrThrow("full_name")));
                u.setRole(cursor.getString(cursor.getColumnIndexOrThrow("role")));
                list.add(u);
            }
            cursor.close();
        }
        return list;
    }

    /**
     * Saves a daily private journal entry locally on-device.
     */
    public JournalResponse saveJournalOffline(String content, String mood, String status) {
        SQLiteDatabase db = getWritableDatabase();
        String id = UUID.randomUUID().toString();
        String now = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(new Date());

        ContentValues cv = new ContentValues();
        cv.put("id", id);
        cv.put("content", content);
        cv.put("mood", mood != null ? mood : "steady");
        cv.put("status", status != null ? status : "SUBMITTED");
        cv.put("created_at", now);

        db.insert(TABLE_JOURNALS, null, cv);
        return new JournalResponse(id, content, mood, status, now);
    }

    /**
     * Retrieves all saved journal entries from local SQLite.
     */
    public List<JournalResponse> getJournalsOffline() {
        List<JournalResponse> list = new ArrayList<>();
        SQLiteDatabase db = getReadableDatabase();
        Cursor cursor = db.query(TABLE_JOURNALS, null, null, null, null, null, "created_at DESC");

        if (cursor != null) {
            while (cursor.moveToNext()) {
                String id = cursor.getString(cursor.getColumnIndexOrThrow("id"));
                String content = cursor.getString(cursor.getColumnIndexOrThrow("content"));
                String mood = cursor.getString(cursor.getColumnIndexOrThrow("mood"));
                String status = cursor.getString(cursor.getColumnIndexOrThrow("status"));
                String createdAt = cursor.getString(cursor.getColumnIndexOrThrow("created_at"));
                list.add(new JournalResponse(id, content, mood, status, createdAt));
            }
            cursor.close();
        }
        return list;
    }

    /**
     * Logs an on-device AI chat message turn.
     */
    public void logChatOffline(String sender, String message, int moraleScore, String matchedProtocol) {
        SQLiteDatabase db = getWritableDatabase();
        ContentValues cv = new ContentValues();
        cv.put("id", UUID.randomUUID().toString());
        cv.put("sender", sender);
        cv.put("message", message);
        cv.put("morale_score", moraleScore);
        cv.put("matched_protocol", matchedProtocol);
        cv.put("created_at", new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(new Date()));
        db.insert(TABLE_CHATS, null, cv);
    }
}
