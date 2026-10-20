package com.parallaxlane.app.api;

import android.content.Context;

import com.google.gson.FieldNamingPolicy;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.parallaxlane.app.BuildConfig;
import com.parallaxlane.app.util.SessionManager;

import java.util.concurrent.TimeUnit;

import okhttp3.OkHttpClient;
import okhttp3.logging.HttpLoggingInterceptor;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;

// Creates the Retrofit services once and shares them with every screen.
public class ApiClient {

    private static ApiService service;
    private static ApiService authService;

    // Returns the service used after login, it sends the token and refreshes it when it expires.
    public static synchronized ApiService get(Context context) {
        if (service == null) {
            Context appContext = context.getApplicationContext();
            SessionManager session = new SessionManager(appContext);
            OkHttpClient client = baseClient()
                    .addInterceptor(new HeaderInterceptor(appContext, session, true))
                    .authenticator(new TokenAuthenticator(session, getAuth(appContext)))
                    .build();
            service = buildRetrofit(client).create(ApiService.class);
        }
        return service;
    }

    // Returns the service used for login and token refresh, it never sends a token.
    public static synchronized ApiService getAuth(Context context) {
        if (authService == null) {
            Context appContext = context.getApplicationContext();
            OkHttpClient client = baseClient()
                    .addInterceptor(new HeaderInterceptor(appContext, new SessionManager(appContext), false))
                    .build();
            authService = buildRetrofit(client).create(ApiService.class);
        }
        return authService;
    }

    // Gson that reads the snake case JSON names of the backend into camel case Java fields.
    public static Gson gson() {
        return new GsonBuilder().setFieldNamingPolicy(FieldNamingPolicy.LOWER_CASE_WITH_UNDERSCORES).create();
    }

    // OkHttp settings shared by both services, logging is on only in debug builds.
    private static OkHttpClient.Builder baseClient() {
        OkHttpClient.Builder builder = new OkHttpClient.Builder()
                .connectTimeout(15, TimeUnit.SECONDS)
                .readTimeout(20, TimeUnit.SECONDS);
        if (BuildConfig.DEBUG) {
            HttpLoggingInterceptor logging = new HttpLoggingInterceptor();
            logging.setLevel(HttpLoggingInterceptor.Level.BASIC);
            builder.addInterceptor(logging);
        }
        return builder;
    }

    // Builds Retrofit with the server address from build.gradle.
    private static Retrofit buildRetrofit(OkHttpClient client) {
        return new Retrofit.Builder()
                .baseUrl(BuildConfig.API_BASE_URL)
                .client(client)
                .addConverterFactory(GsonConverterFactory.create(gson()))
                .build();
    }
}
