package com.example.myapplication;

import android.os.Bundle;
import android.text.TextUtils;
import android.view.View;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.lifecycle.ViewModelProvider;

import com.example.myapplication.api.ApiClient;
import com.example.myapplication.api.SentinelApiService;
import com.example.myapplication.auth.AuthManager;
import com.example.myapplication.databinding.ActivityMainBinding;
import com.example.myapplication.models.UserResponse;
import com.example.myapplication.models.ChatResponse;
import com.example.myapplication.models.JournalResponse;

import java.util.Calendar;
import java.util.List;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class MainActivity extends AppCompatActivity {

    private ActivityMainBinding binding;
    private MainViewModel viewModel;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        binding = ActivityMainBinding.inflate(getLayoutInflater());
        setContentView(binding.getRoot());

        AuthManager authManager = new AuthManager(this);
        SentinelApiService apiService = ApiClient.getClient(authManager).create(SentinelApiService.class);

        MainViewModel.Factory factory = new MainViewModel.Factory(authManager, apiService, this);
        viewModel = new ViewModelProvider(this, factory).get(MainViewModel.class);

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

        responseText.setText("Consulting CRPF Mental Health On-Device Neural Engine...");
        viewModel.sendChat(message, null, new Callback<>() {
            @Override
            public void onResponse(@NonNull Call<ChatResponse> call, @NonNull Response<ChatResponse> response) {
                if (response.isSuccessful() && response.body() != null && response.body().getMessage() != null) {
                    responseText.setText(response.body().getMessage().getContent());
                    if (companionInput != null) {
                        companionInput.setText("");
                    }
                    if (response.body().isSupportEscalation()) {
                        Toast.makeText(MainActivity.this, "CRPF Crisis Protocol: Please use Get Support for confidential assistance.", Toast.LENGTH_LONG).show();
                    }
                } else {
                    responseText.setText("Your companion is unavailable right now. Please try again or contact support.");
                }
            }

            @Override
            public void onFailure(@NonNull Call<ChatResponse> call, @NonNull Throwable throwable) {
                responseText.setText("Your companion is unavailable right now. Please check your connection.");
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
        viewModel.saveJournal(content, "okay", "SUBMITTED", new Callback<>() {
            @Override
            public void onResponse(@NonNull Call<JournalResponse> call, @NonNull Response<JournalResponse> response) {
                if (response.isSuccessful()) {
                    journalInput.setText("");
                    Toast.makeText(MainActivity.this, "Your private journal entry was saved.", Toast.LENGTH_SHORT).show();
                } else {
                    Toast.makeText(MainActivity.this, "We could not save your journal entry.", Toast.LENGTH_LONG).show();
                }
            }

            @Override
            public void onFailure(@NonNull Call<JournalResponse> call, @NonNull Throwable throwable) {
                Toast.makeText(MainActivity.this, "Connection unavailable. Your entry was not submitted.", Toast.LENGTH_LONG).show();
            }
        });
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
}
