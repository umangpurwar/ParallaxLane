package com.parallaxlane.app.ui;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ProgressBar;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;

import com.parallaxlane.app.R;
import com.parallaxlane.app.api.ApiClient;
import com.parallaxlane.app.api.ApiError;
import com.parallaxlane.app.model.ApiModels;
import com.parallaxlane.app.util.SessionManager;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

// First screen, signs the student in with email and password.
public class LoginActivity extends AppCompatActivity {

    private EditText emailInput;
    private EditText passwordInput;
    private Button loginButton;
    private ProgressBar progressBar;
    private SessionManager session;

    // Skips this screen when already signed in, otherwise shows the login form.
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        session = new SessionManager(this);
        if (session.isLoggedIn()) {
            openDeviceScreen();
            return;
        }
        setContentView(R.layout.activity_login);
        emailInput = findViewById(R.id.emailInput);
        passwordInput = findViewById(R.id.passwordInput);
        loginButton = findViewById(R.id.loginButton);
        progressBar = findViewById(R.id.progressBar);
        loginButton.setOnClickListener(v -> login());
    }

    // Checks the fields and sends the login request to the backend.
    private void login() {
        String email = emailInput.getText().toString().trim().toLowerCase();
        String password = passwordInput.getText().toString();
        if (email.isEmpty() || password.isEmpty()) {
            Toast.makeText(this, "Enter email and password", Toast.LENGTH_SHORT).show();
            return;
        }
        setLoading(true);
        ApiClient.getAuth(this).login(new ApiModels.LoginRequest(email, password))
                .enqueue(new Callback<ApiModels.LoginResponse>() {
                    // Runs when the server answers.
                    @Override
                    public void onResponse(@NonNull Call<ApiModels.LoginResponse> call, @NonNull Response<ApiModels.LoginResponse> response) {
                        if (isDestroyed()) return;
                        setLoading(false);
                        if (response.isSuccessful() && response.body() != null) {
                            session.saveLogin(response.body());
                            openDeviceScreen();
                        } else {
                            Toast.makeText(LoginActivity.this, ApiError.from(response).message, Toast.LENGTH_LONG).show();
                        }
                    }

                    // Runs when the server could not be reached.
                    @Override
                    public void onFailure(@NonNull Call<ApiModels.LoginResponse> call, @NonNull Throwable t) {
                        if (isDestroyed()) return;
                        setLoading(false);
                        Toast.makeText(LoginActivity.this, R.string.network_error, Toast.LENGTH_LONG).show();
                    }
                });
    }

    // Shows or hides the progress bar and blocks the button while waiting.
    private void setLoading(boolean loading) {
        progressBar.setVisibility(loading ? View.VISIBLE : View.GONE);
        loginButton.setEnabled(!loading);
    }

    // Moves to the phone approval screen and closes this one.
    private void openDeviceScreen() {
        startActivity(new Intent(this, DeviceActivity.class));
        finish();
    }
}
