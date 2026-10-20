package com.parallaxlane.app.api;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

import com.parallaxlane.app.model.ApiModels;
import com.parallaxlane.app.util.SessionManager;

import java.io.IOException;

import okhttp3.Authenticator;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.Route;

// OkHttp calls this when the server says the access token expired, it gets new tokens once and retries the request.
public class TokenAuthenticator implements Authenticator {

    private final SessionManager session;
    private final ApiService authService;

    // Takes the session and a Retrofit service that does not use this authenticator.
    public TokenAuthenticator(SessionManager session, ApiService authService) {
        this.session = session;
        this.authService = authService;
    }

    // Returns the request again with a new token, or null to stop trying, synchronized so two requests never refresh at the same time.
    @Nullable
    @Override
    public synchronized Request authenticate(@Nullable Route route, @NonNull Response response) throws IOException {
        if (response.priorResponse() != null) {
            return null;
        }
        String sentToken = response.request().header("Authorization");
        String savedToken = session.getAccessToken();
        if (savedToken != null && !("Bearer " + savedToken).equals(sentToken)) {
            return response.request().newBuilder().header("Authorization", "Bearer " + savedToken).build();
        }
        String refresh = session.getRefreshToken();
        if (refresh == null) {
            return null;
        }
        retrofit2.Response<ApiModels.RefreshResponse> result =
                authService.refresh(new ApiModels.RefreshRequest(refresh)).execute();
        if (result.isSuccessful() && result.body() != null) {
            session.saveTokens(result.body().access, result.body().refresh);
            return response.request().newBuilder().header("Authorization", "Bearer " + result.body().access).build();
        }
        session.clear();
        return null;
    }
}
