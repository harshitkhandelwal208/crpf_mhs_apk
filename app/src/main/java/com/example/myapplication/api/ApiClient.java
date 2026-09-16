package com.example.myapplication.api;

import okhttp3.OkHttpClient;
import okhttp3.logging.HttpLoggingInterceptor;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;
import com.example.myapplication.auth.AuthInterceptor;
import com.example.myapplication.auth.AuthManager;
import com.example.myapplication.auth.TokenAuthenticator;

public class ApiClient {
    // Note: Use 10.0.2.2 for localhost access from Android Emulator
    // Android emulator -> host machine. Use the host LAN IP for a physical device.
    private static final String BASE_URL = "http://10.0.2.2:8000/";
    private static Retrofit retrofit = null;

    public static Retrofit getClient(AuthManager authManager) {
        if (retrofit == null) {
            HttpLoggingInterceptor logging = new HttpLoggingInterceptor();
            logging.setLevel(HttpLoggingInterceptor.Level.BODY);

            OkHttpClient client = new OkHttpClient.Builder()
                    .addInterceptor(logging)
                    .addInterceptor(new AuthInterceptor(authManager))
                    .authenticator(new TokenAuthenticator(authManager, BASE_URL))
                    .build();

            retrofit = new Retrofit.Builder()
                    .baseUrl(BASE_URL)
                    .client(client)
                    .addConverterFactory(GsonConverterFactory.create())
                    .build();
        }
        return retrofit;
    }
}
