package com.example.myapplication.api;

import com.example.myapplication.models.LoginRequest;
import com.example.myapplication.models.RefreshRequest;
import com.example.myapplication.models.TokenResponse;
import com.example.myapplication.models.UserResponse;
import com.example.myapplication.models.ChatRequest;
import com.example.myapplication.models.ChatResponse;
import com.example.myapplication.models.JournalRequest;
import com.example.myapplication.models.JournalResponse;
import com.example.myapplication.models.SupportRequest;
import com.example.myapplication.models.SupportResponse;
import com.example.myapplication.models.VoiceTranscriptionResponse;


import okhttp3.MultipartBody;
import retrofit2.Call;
import retrofit2.http.Body;
import retrofit2.http.GET;
import retrofit2.http.Multipart;
import retrofit2.http.Part;
import retrofit2.http.POST;

public interface SentinelApiService {

    @POST("api/auth/login")
    Call<TokenResponse> login(@Body LoginRequest request);

    @POST("api/auth/refresh")
    Call<TokenResponse> refreshToken(@Body RefreshRequest request);

    @GET("api/users/me")
    Call<UserResponse> getUserProfile();

    @POST("api/ai/chat")
    Call<ChatResponse> sendChat(@Body ChatRequest request);

    @POST("api/journals")
    Call<JournalResponse> createJournal(@Body JournalRequest request);


    @Multipart
    @POST("api/voice/transcribe")
    Call<VoiceTranscriptionResponse> transcribeVoice(@Part MultipartBody.Part audio);

    @POST("api/support/request")
    Call<SupportResponse> createSupportRequest(@Body SupportRequest request);
}
