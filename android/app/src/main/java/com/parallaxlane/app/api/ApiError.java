package com.parallaxlane.app.api;

import com.google.gson.JsonObject;

import retrofit2.Response;

// Reads the error code and message the backend sends when a request fails.
public class ApiError {

    public String code = "unknown";
    public String message = "Something went wrong. Try again.";
    public int httpCode;

    // Builds an ApiError from a failed Retrofit response.
    public static ApiError from(Response<?> response) {
        ApiError error = new ApiError();
        error.httpCode = response.code();
        if (response.code() == 429) {
            error.code = "rate_limited";
            error.message = "Too many attempts. Wait a minute and try again.";
            return error;
        }
        if (response.code() == 426) {
            error.code = "app_update_required";
            error.message = "This app version is too old. Please update the app.";
            return error;
        }
        try {
            JsonObject json = ApiClient.gson().fromJson(response.errorBody().charStream(), JsonObject.class);
            if (json.has("code")) {
                error.code = json.get("code").getAsString();
            }
            if (json.has("error")) {
                error.message = json.get("error").getAsString();
            } else if (json.has("detail")) {
                error.message = json.get("detail").getAsString();
            } else if (json.has("non_field_errors")) {
                error.message = json.getAsJsonArray("non_field_errors").get(0).getAsString();
            }
        } catch (Exception ignored) {
            // Keeps the default message when the body is not JSON.
        }
        return error;
    }

    // Tells whether the login session ended and the user must sign in again.
    public boolean sessionExpired() {
        return httpCode == 401;
    }

    // Tells whether the exam attempt has already ended on the server.
    public boolean attemptEnded() {
        return "attempt_ended".equals(code) || "attempt_terminated".equals(code);
    }
}
