package com.example.myapplication.api;

import android.content.Context;

import com.example.myapplication.BuildConfig;
import com.example.myapplication.auth.AuthInterceptor;
import com.example.myapplication.auth.AuthManager;
import com.example.myapplication.auth.TokenAuthenticator;

import java.io.File;
import java.util.concurrent.TimeUnit;

import okhttp3.Cache;
import okhttp3.ConnectionPool;
import okhttp3.OkHttpClient;
import okhttp3.logging.HttpLoggingInterceptor;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;

public final class ApiClient {
    private static final long HTTP_CACHE_BYTES = 5L * 1024L * 1024L;
    private static final String BASE_URL = ensureTrailingSlash(BuildConfig.SENTINEL_API_BASE_URL);

    private static volatile Retrofit retrofit;

    private ApiClient() {
    }

    public static Retrofit getClient(Context context, AuthManager authManager) {
        Retrofit current = retrofit;
        if (current == null) {
            synchronized (ApiClient.class) {
                current = retrofit;
                if (current == null) {
                    Context appContext = context.getApplicationContext();
                    HttpLoggingInterceptor logging = new HttpLoggingInterceptor();
                    logging.redactHeader("Authorization");
                    logging.redactHeader("Cookie");
                    logging.setLevel(BuildConfig.DEBUG
                            ? HttpLoggingInterceptor.Level.BASIC
                            : HttpLoggingInterceptor.Level.NONE);

                    OkHttpClient client = new OkHttpClient.Builder()
                            .connectTimeout(10, TimeUnit.SECONDS)
                            .readTimeout(20, TimeUnit.SECONDS)
                            .writeTimeout(20, TimeUnit.SECONDS)
                            .callTimeout(30, TimeUnit.SECONDS)
                            .connectionPool(new ConnectionPool(5, 5, TimeUnit.MINUTES))
                            .cache(new Cache(new File(appContext.getCacheDir(), "sentinel_http"), HTTP_CACHE_BYTES))
                            .retryOnConnectionFailure(true)
                            .addInterceptor(logging)
                            .addInterceptor(new AuthInterceptor(authManager))
                            .authenticator(new TokenAuthenticator(authManager, BASE_URL))
                            .build();

                    current = new Retrofit.Builder()
                            .baseUrl(BASE_URL)
                            .client(client)
                            .addConverterFactory(GsonConverterFactory.create())
                            .build();
                    retrofit = current;
                }
            }
        }
        return current;
    }

    private static String ensureTrailingSlash(String value) {
        return value.endsWith("/") ? value : value + "/";
    }
}
