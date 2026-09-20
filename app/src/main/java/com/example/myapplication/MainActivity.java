package com.example.myapplication;

import android.os.Bundle;
import android.text.TextUtils;
import android.view.View;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.ContextCompat;
import androidx.lifecycle.ViewModelProvider;

import com.example.myapplication.api.ApiClient;
import com.example.myapplication.api.SentinelApiService;
import com.example.myapplication.auth.AuthManager;
import com.example.myapplication.databinding.ActivityMainBinding;
import com.example.myapplication.models.UserResponse;
import com.example.myapplication.models.ChatResponse;
import com.example.myapplication.models.JournalResponse;
import com.example.myapplication.ai.HKWhisperEngine;
import com.example.myapplication.ai.SentinelTTSManager;
import com.example.myapplication.sync.JournalSyncStatus;

import java.util.Calendar;
import java.util.List;

public class MainActivity extends AppCompatActivity {

    private static final int REQUEST_RECORD_AUDIO_PERMISSION = 201;

    private ActivityMainBinding binding;
    private MainViewModel viewModel;
    private SentinelTTSManager ttsManager;
    private HKWhisperEngine whisperEngine;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        binding = ActivityMainBinding.inflate(getLayoutInflater());
        setContentView(binding.getRoot());

        AuthManager authManager = new AuthManager(this);
        SentinelApiService apiService = ApiClient.getClient(this, authManager).create(SentinelApiService.class);

        MainViewModel.Factory factory = new MainViewModel.Factory(authManager, apiService, this);
        viewModel = new ViewModelProvider(this, factory).get(MainViewModel.class);

        ttsManager = new SentinelTTSManager(this);
        whisperEngine = new HKWhisperEngine(viewModel.getPipeline().getKnowledgeBase());

        ttsManager.setStateListener(new SentinelTTSManager.TTSStateListener() {
            @Override
            public void onSpeechStarted() {
                runOnUiThread(() -> {
                    View stopBtn = findViewById(R.id.companion_tts_stop_button);
                    if (stopBtn != null) stopBtn.setVisibility(View.VISIBLE);
                });
            }

            @Override
            public void onSpeechCompleted() {
                runOnUiThread(() -> {
                    View stopBtn = findViewById(R.id.companion_tts_stop_button);
                    if (stopBtn != null) stopBtn.setVisibility(View.GONE);
                });
            }

            @Override
            public void onSpeechError(String message) {
                runOnUiThread(() -> {
                    View stopBtn = findViewById(R.id.companion_tts_stop_button);
                    if (stopBtn != null) stopBtn.setVisibility(View.GONE);
                });
            }
        });

        setupListeners();
        observeViewModel();

        if (authManager.isLoggedIn() && viewModel.userProfile.getValue() == null) {
            viewModel.loadProfile();
        }
    }

    private void setupListeners() {
        binding.loginButton.setOnClickListener(view -> {
            String email = binding.emailInput.getText() == null
                    ? "" : binding.emailInput.getText().toString().trim();
            String password = binding.passwordInput.getText() == null
                    ? "" : binding.passwordInput.getText().toString();

            if (TextUtils.isEmpty(email) || TextUtils.isEmpty(password)) {
                showLoginError(getString(R.string.error_enter_credentials));
                return;
            }
            viewModel.login(email, password);
        });

        binding.registerButton.setOnClickListener(view -> showRegisterDialog());

        binding.logoutButton.setOnClickListener(view -> viewModel.logout());

        binding.navHome.setOnClickListener(view -> showScreen("home"));
        binding.navJournal.setOnClickListener(view -> showScreen("journal"));
        binding.navCompanion.setOnClickListener(view -> showScreen("companion"));
        binding.navHistory.setOnClickListener(view -> showScreen("history"));
        binding.navProfile.setOnClickListener(view -> showScreen("profile"));
        binding.dailyLogButton.setOnClickListener(view -> showScreen("journal"));
        binding.supportButton.setOnClickListener(view -> showScreen("profile"));
        findViewById(R.id.history_journal_button).setOnClickListener(view -> showScreen("journal"));
        findViewById(R.id.profile_support_button).setOnClickListener(view -> showScreen("support"));
        findViewById(R.id.profile_resources_button).setOnClickListener(view -> showScreen("resources"));
        findViewById(R.id.profile_settings_button).setOnClickListener(view ->
            Toast.makeText(this, "Consent and notification settings are coming next.", Toast.LENGTH_SHORT).show());
        findViewById(R.id.journal_assessment_button).setOnClickListener(view -> showScreen("assessment"));
        findViewById(R.id.journal_voice_button).setOnClickListener(view -> showScreen("voice"));
        findViewById(R.id.companion_start_button).setOnClickListener(view -> sendCompanionMessage());
        findViewById(R.id.journal_save_button).setOnClickListener(view -> saveJournalEntry());

        // Multimodal AI Action Listeners
        findViewById(R.id.companion_tts_button).setOnClickListener(view -> playCompanionTTS());
        findViewById(R.id.companion_tts_stop_button).setOnClickListener(view -> {
            if (ttsManager != null) ttsManager.stop();
        });
        findViewById(R.id.companion_voice_input_button).setOnClickListener(view -> showScreen("voice"));
        findViewById(R.id.voice_record_button).setOnClickListener(view -> toggleVoiceRecording());
        findViewById(R.id.voice_save_journal_button).setOnClickListener(view -> saveVoiceTranscriptToJournal());
        findViewById(R.id.voice_send_companion_button).setOnClickListener(view -> sendVoiceTranscriptToCompanion());
    }

    private void observeViewModel() {
        viewModel.isLoggedIn.observe(this, loggedIn -> {
            if (!loggedIn) {
                showLoginPanel();
                if (viewModel.userProfile.getValue() != null) {
                    Toast.makeText(this, R.string.msg_signed_out, Toast.LENGTH_SHORT).show();
                }
            }
        });

        viewModel.userProfile.observe(this, user -> {
            if (user != null) {
                showDashboard(user);
            }
        });

        viewModel.isLoading.observe(this, this::setLoginLoading);
        viewModel.journalSyncStatus.observe(this, this::renderJournalSyncStatus);

        viewModel.errorMessageResId.observe(this, resId -> {
            if (resId != null) {
                showLoginError(getString(resId));
                viewModel.clearError();
            }
        });
    }

    private void showLoginPanel() {
        binding.dashboardPanel.setVisibility(View.GONE);
        binding.journalPanel.getRoot().setVisibility(View.GONE);
        binding.companionPanel.getRoot().setVisibility(View.GONE);
        binding.historyPanel.getRoot().setVisibility(View.GONE);
        binding.profilePanel.getRoot().setVisibility(View.GONE);
        binding.assessmentPanel.getRoot().setVisibility(View.GONE);
        binding.voicePanel.getRoot().setVisibility(View.GONE);
        binding.supportPanel.getRoot().setVisibility(View.GONE);
        binding.resourcesPanel.getRoot().setVisibility(View.GONE);
        binding.screenNav.setVisibility(View.GONE);
        binding.loginPanel.setVisibility(View.VISIBLE);
        binding.passwordInput.setText("");
        binding.loginError.setVisibility(View.GONE);
    }

    private void showDashboard(UserResponse user) {
        String fullName = TextUtils.isEmpty(user.getFullName()) ? "Personnel member" : user.getFullName();
        binding.nameText.setText(fullName);
        binding.emailText.setText(user.getEmail());
        binding.roleText.setText(R.string.role_personnel_active);
        binding.avatarText.setText(initialsFor(fullName));
        binding.welcomeText.setText(getString(R.string.welcome_greeting, greeting(), firstNameOf(fullName)));
        binding.loginPanel.setVisibility(View.GONE);
        binding.screenNav.setVisibility(View.VISIBLE);
        showScreen("home");
    }

    private void showScreen(String screen) {
        binding.loginPanel.setVisibility(View.GONE);
        binding.dashboardPanel.setVisibility(View.GONE);
        binding.journalPanel.getRoot().setVisibility(View.GONE);
        binding.companionPanel.getRoot().setVisibility(View.GONE);
        binding.historyPanel.getRoot().setVisibility(View.GONE);
        binding.profilePanel.getRoot().setVisibility(View.GONE);
        binding.assessmentPanel.getRoot().setVisibility(View.GONE);
        binding.voicePanel.getRoot().setVisibility(View.GONE);
        binding.supportPanel.getRoot().setVisibility(View.GONE);
        binding.resourcesPanel.getRoot().setVisibility(View.GONE);

        switch (screen) {
            case "journal":
                binding.journalPanel.getRoot().setVisibility(View.VISIBLE);
                break;
            case "companion":
                binding.companionPanel.getRoot().setVisibility(View.VISIBLE);
                break;
            case "history":
                List<JournalResponse> journals = viewModel.getSavedJournals();
                TextView historyText = findViewById(R.id.history_text);
                if (journals != null && !journals.isEmpty()) {
                    StringBuilder sb = new StringBuilder();
                    for (int i = 0; i < Math.min(6, journals.size()); i++) {
                        JournalResponse j = journals.get(i);
                        sb.append("• [").append(j.getCreatedAt() != null ? j.getCreatedAt() : "Offline Entry").append("] (Mood: ").append(j.getMood() != null ? j.getMood() : "okay").append(")\n")
                          .append(j.getContent()).append("\n\n");
                    }
                    historyText.setText(sb.toString().trim());
                } else {
                    historyText.setText("No saved offline entries yet. Write a daily log or check-in to preserve your thoughts.");
                }
                binding.historyPanel.getRoot().setVisibility(View.VISIBLE);
                break;
            case "profile":
                UserResponse user = viewModel.userProfile.getValue();
                if (user != null) {
                    TextView profileName = findViewById(R.id.profile_name_text);
                    TextView profileEmail = findViewById(R.id.profile_email_text);
                    profileName.setText(user.getFullName());
                    profileEmail.setText(user.getEmail());
                }
                binding.profilePanel.getRoot().setVisibility(View.VISIBLE);
                break;
            case "assessment":
                binding.assessmentPanel.getRoot().setVisibility(View.VISIBLE);
                break;
            case "voice":
                binding.voicePanel.getRoot().setVisibility(View.VISIBLE);
                break;
            case "support":
                binding.supportPanel.getRoot().setVisibility(View.VISIBLE);
                break;
            case "resources":
                binding.resourcesPanel.getRoot().setVisibility(View.VISIBLE);
                break;
            case "home":
            default:
                binding.dashboardPanel.setVisibility(View.VISIBLE);
                break;
        }
        binding.screenNav.setVisibility(View.VISIBLE);
    }

    private void sendCompanionMessage() {
        TextView responseText = findViewById(R.id.companion_response_text);
        TextView companionInput = findViewById(R.id.companion_input);
        String message = companionInput != null && companionInput.getText() != null && !companionInput.getText().toString().trim().isEmpty()
                ? companionInput.getText().toString().trim()
                : "I would like to talk through how I am feeling today.";

        responseText.setText(R.string.status_local_companion_thinking);
        viewModel.sendChat(message, null, new MainViewModel.LocalResultCallback<>() {
            @Override
            public void onSuccess(ChatResponse response) {
                if (response != null && response.getMessage() != null) {
                    responseText.setText(response.getMessage().getContent());
                    TextView triageBadge = findViewById(R.id.companion_triage_badge);
                    if (triageBadge != null && response.getTriageClass() != null) {
                        triageBadge.setText(String.format("DistilBERT: %s (%.0f%%)",
                                response.getTriageClass(), response.getConfidence() * 100));
                    }
                    if (companionInput != null) {
                        companionInput.setText("");
                    }
                    if (response.isSupportEscalation()) {
                        Toast.makeText(MainActivity.this, R.string.msg_crisis_support, Toast.LENGTH_LONG).show();
                    }
                } else {
                    responseText.setText(R.string.error_companion_unavailable);
                }
            }

            @Override
            public void onError(Throwable throwable) {
                responseText.setText(R.string.error_companion_unavailable);
            }
        });
    }

    private void saveJournalEntry() {
        TextView journalInput = findViewById(R.id.journal_input);
        String content = journalInput.getText() == null ? "" : journalInput.getText().toString().trim();
        if (content.isEmpty()) {
            journalInput.setError("Write something before saving");
            return;
        }
        viewModel.saveJournal(content, "okay", "SUBMITTED", new MainViewModel.LocalResultCallback<>() {
            @Override
            public void onSuccess(JournalResponse response) {
                journalInput.setText("");
                Toast.makeText(MainActivity.this, R.string.msg_journal_saved_locally, Toast.LENGTH_SHORT).show();
            }

            @Override
            public void onError(Throwable throwable) {
                Toast.makeText(MainActivity.this, R.string.error_journal_local_save, Toast.LENGTH_LONG).show();
            }
        });
    }

    private void renderJournalSyncStatus(JournalSyncStatus status) {
        if (status == null) {
            return;
        }
        int textRes;
        int colorRes;
        switch (status) {
            case SYNCING:
                textRes = R.string.sync_status_syncing;
                colorRes = R.color.teal_700;
                break;
            case SAVED_OFFLINE:
                textRes = R.string.sync_status_saved_offline;
                colorRes = R.color.warning;
                break;
            case SYNCED:
            default:
                textRes = R.string.sync_status_synced;
                colorRes = R.color.success;
                break;
        }

        int color = ContextCompat.getColor(this, colorRes);
        TextView dashboardStatus = findViewById(R.id.dashboard_sync_status);
        TextView journalStatus = findViewById(R.id.journal_sync_status);
        dashboardStatus.setText(textRes);
        dashboardStatus.setTextColor(color);
        dashboardStatus.setContentDescription(getString(textRes));
        journalStatus.setText(textRes);
        journalStatus.setTextColor(color);
        journalStatus.setContentDescription(getString(textRes));
    }

    private void setLoginLoading(boolean loading) {
        binding.loginButton.setEnabled(!loading);
        binding.loginButton.setText(loading ? R.string.status_signing_in : R.string.action_continue_dashboard);
    }

    private void showLoginError(String message) {
        binding.loginPanel.setVisibility(View.VISIBLE);
        binding.dashboardPanel.setVisibility(View.GONE);
        binding.loginError.setText(message);
        binding.loginError.setVisibility(View.VISIBLE);
    }

    private String firstNameOf(String fullName) {
        int separator = fullName.indexOf(' ');
        return separator > 0 ? fullName.substring(0, separator) : fullName;
    }

    private String initialsFor(String fullName) {
        String[] names = fullName.trim().split("\\s+");
        if (names.length == 1) {
            return names[0].substring(0, Math.min(2, names[0].length())).toUpperCase();
        }
        return (names[0].charAt(0) + "" + names[names.length - 1].charAt(0)).toUpperCase();
    }

    private String greeting() {
        int hour = Calendar.getInstance().get(Calendar.HOUR_OF_DAY);
        if (hour < 12) return "Good morning";
        if (hour < 18) return "Good afternoon";
        return "Good evening";
    }

    private void showRegisterDialog() {
        android.widget.LinearLayout layout = new android.widget.LinearLayout(this);
        layout.setOrientation(android.widget.LinearLayout.VERTICAL);
        layout.setPadding(48, 24, 48, 24);

        final android.widget.EditText serviceInput = new android.widget.EditText(this);
        serviceInput.setHint("Service Number (e.g. CRPF-98214)");
        layout.addView(serviceInput);

        final android.widget.EditText nameInput = new android.widget.EditText(this);
        nameInput.setHint("Full Name (e.g. Amit Sharma)");
        layout.addView(nameInput);

        final android.widget.EditText rankInput = new android.widget.EditText(this);
        rankInput.setHint("Rank (e.g. Head Constable)");
        rankInput.setText("Head Constable");
        layout.addView(rankInput);

        final android.widget.EditText unitInput = new android.widget.EditText(this);
        unitInput.setHint("Unit (e.g. 110 Bn CRPF)");
        unitInput.setText("110 Bn CRPF");
        layout.addView(unitInput);

        final android.widget.EditText emailInput = new android.widget.EditText(this);
        emailInput.setHint("Email address");
        emailInput.setInputType(android.text.InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS);
        layout.addView(emailInput);

        final android.widget.EditText passwordInput = new android.widget.EditText(this);
        passwordInput.setHint("Password (min 8 chars)");
        passwordInput.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);
        layout.addView(passwordInput);

        new androidx.appcompat.app.AlertDialog.Builder(this)
                .setTitle("New Personnel Registration")
                .setMessage("Register your personnel profile on the secure CRPF MHS platform.")
                .setView(layout)
                .setPositiveButton("Register & Enrol", (dialog, which) -> {
                    String serviceNo = serviceInput.getText().toString().trim();
                    String fullName = nameInput.getText().toString().trim();
                    String rank = rankInput.getText().toString().trim();
                    String unit = unitInput.getText().toString().trim();
                    String email = emailInput.getText().toString().trim();
                    String password = passwordInput.getText().toString();

                    if (TextUtils.isEmpty(serviceNo) || TextUtils.isEmpty(fullName)
                            || TextUtils.isEmpty(email) || TextUtils.isEmpty(password)) {
                        Toast.makeText(this, "Please fill in all mandatory registration fields", Toast.LENGTH_SHORT).show();
                        return;
                    }

                    String[] parts = fullName.split("\\s+", 2);
                    String firstName = parts[0];
                    String lastName = parts.length > 1 ? parts[1] : "-";

                    viewModel.register(serviceNo, email, password, firstName, lastName, rank, unit, null);
                })
                .setNegativeButton("Cancel", null)
                .show();
    }

    private void toggleVoiceRecording() {
        if (ContextCompat.checkSelfPermission(this, android.Manifest.permission.RECORD_AUDIO)
                != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            androidx.core.app.ActivityCompat.requestPermissions(
                    this,
                    new String[]{android.Manifest.permission.RECORD_AUDIO},
                    REQUEST_RECORD_AUDIO_PERMISSION
            );
            return;
        }

        com.google.android.material.button.MaterialButton recordBtn = findViewById(R.id.voice_record_button);
        TextView statusText = findViewById(R.id.voice_status_text);
        View transcriptContainer = findViewById(R.id.voice_transcript_container);
        TextView transcriptText = findViewById(R.id.voice_transcript_text);

        if (!whisperEngine.isRecording()) {
            if (transcriptContainer != null) transcriptContainer.setVisibility(View.GONE);
            boolean started = whisperEngine.startRecording(
                    (normalizedRms, decibels) -> {
                        if (statusText != null) {
                            statusText.setText(String.format("Listening... Audio level: %d dB", decibels));
                        }
                    },
                    new HKWhisperEngine.TranscriptionCallback() {
                        @Override
                        public void onPartialTranscription(String partial) {
                            runOnUiThread(() -> {
                                if (statusText != null) statusText.setText(partial);
                            });
                        }

                        @Override
                        public void onTranscriptionComplete(String fullText, float confidence) {
                            runOnUiThread(() -> {
                                if (statusText != null) {
                                    statusText.setText(String.format("Whisper Base-EN: Transcribed (%.0f%% confidence)", confidence * 100));
                                }
                                if (transcriptText != null) {
                                    transcriptText.setText(fullText);
                                }
                                if (transcriptContainer != null) {
                                    transcriptContainer.setVisibility(View.VISIBLE);
                                }
                                if (recordBtn != null) {
                                    recordBtn.setText("Start speaking");
                                }
                            });
                        }

                        @Override
                        public void onError(String errorMessage) {
                            runOnUiThread(() -> {
                                if (statusText != null) statusText.setText("Error: " + errorMessage);
                                if (recordBtn != null) recordBtn.setText("Start speaking");
                            });
                        }
                    }
            );

            if (started) {
                if (recordBtn != null) recordBtn.setText("Stop speaking");
                if (statusText != null) statusText.setText("Listening with Whisper Base-EN...");
            } else {
                Toast.makeText(this, "Could not start microphone recording", Toast.LENGTH_SHORT).show();
            }
        } else {
            whisperEngine.stopRecording();
            if (recordBtn != null) recordBtn.setText("Start speaking");
            if (statusText != null) statusText.setText("Transcribing on-device with Whisper Base-EN...");
        }
    }

    private void saveVoiceTranscriptToJournal() {
        TextView transcriptText = findViewById(R.id.voice_transcript_text);
        if (transcriptText == null || TextUtils.isEmpty(transcriptText.getText())) return;
        String content = transcriptText.getText().toString().trim();
        viewModel.saveJournal(content, "okay", "SUBMITTED", new MainViewModel.LocalResultCallback<>() {
            @Override
            public void onSuccess(JournalResponse response) {
                Toast.makeText(MainActivity.this, "Voice entry saved to private journal!", Toast.LENGTH_SHORT).show();
                showScreen("journal");
            }

            @Override
            public void onError(Throwable throwable) {
                Toast.makeText(MainActivity.this, R.string.error_journal_local_save, Toast.LENGTH_SHORT).show();
            }
        });
    }

    private void sendVoiceTranscriptToCompanion() {
        TextView transcriptText = findViewById(R.id.voice_transcript_text);
        if (transcriptText == null || TextUtils.isEmpty(transcriptText.getText())) return;
        String content = transcriptText.getText().toString().trim();
        showScreen("companion");
        TextView companionInput = findViewById(R.id.companion_input);
        if (companionInput != null) {
            companionInput.setText(content);
        }
        sendCompanionMessage();
    }

    private void playCompanionTTS() {
        TextView responseText = findViewById(R.id.companion_response_text);
        if (responseText != null && !TextUtils.isEmpty(responseText.getText()) && ttsManager != null) {
            ttsManager.speak(responseText.getText().toString());
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQUEST_RECORD_AUDIO_PERMISSION) {
            if (grantResults.length > 0 && grantResults[0] == android.content.pm.PackageManager.PERMISSION_GRANTED) {
                toggleVoiceRecording();
            } else {
                Toast.makeText(this, "Microphone permission is required for voice journaling.", Toast.LENGTH_LONG).show();
            }
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (ttsManager != null) {
            ttsManager.stop();
        }
        if (whisperEngine != null && whisperEngine.isRecording()) {
            whisperEngine.stopRecording();
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (ttsManager != null) {
            ttsManager.shutdown();
        }
        if (whisperEngine != null && whisperEngine.isRecording()) {
            whisperEngine.stopRecording();
        }
    }
}
