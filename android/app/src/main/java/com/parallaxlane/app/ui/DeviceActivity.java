package com.parallaxlane.app.ui;

import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;

import com.parallaxlane.app.R;
import com.parallaxlane.app.api.ApiClient;
import com.parallaxlane.app.api.ApiError;
import com.parallaxlane.app.model.ApiModels;
import com.parallaxlane.app.util.AppUtils;
import com.parallaxlane.app.util.DeviceHelper;

import java.util.List;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

// Registers this phone with the backend and waits until the admin approves it.
public class DeviceActivity extends AppCompatActivity {

    private TextView statusText;
    private TextView noteText;
    private ProgressBar progressBar;
    private String deviceId;

    // Shows the phone details and registers the phone right away.
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_device);
        setTitle(R.string.device_title);
        statusText = findViewById(R.id.statusText);
        noteText = findViewById(R.id.noteText);
        progressBar = findViewById(R.id.progressBar);
        TextView modelText = findViewById(R.id.modelText);
        TextView phoneIdText = findViewById(R.id.phoneIdText);
        Button checkButton = findViewById(R.id.checkButton);
        Button signOutButton = findViewById(R.id.signOutButton);

        deviceId = DeviceHelper.getDeviceId(this);
        modelText.setText(Build.MANUFACTURER + " " + Build.MODEL);
        phoneIdText.setText("Phone ID " + deviceId.substring(0, 16));

        checkButton.setOnClickListener(v -> checkStatus());
        signOutButton.setOnClickListener(v -> AppUtils.logoutToLogin(this));
        registerPhone();
    }

    // Sends the phone id and public key to the backend, the first phone of an account is approved at once.
    private void registerPhone() {
        String publicKey;
        try {
            publicKey = DeviceHelper.getPublicKey();
        } catch (Exception e) {
            Toast.makeText(this, "This phone cannot create a secure key", Toast.LENGTH_LONG).show();
            return;
        }
        progressBar.setVisibility(View.VISIBLE);
        ApiModels.DeviceRequest request = new ApiModels.DeviceRequest(deviceId, publicKey, Build.MANUFACTURER + " " + Build.MODEL);
        ApiClient.get(this).registerDevice(request).enqueue(new Callback<ApiModels.Device>() {
            // Runs when the server answers.
            @Override
            public void onResponse(@NonNull Call<ApiModels.Device> call, @NonNull Response<ApiModels.Device> response) {
                if (isDestroyed()) return;
                progressBar.setVisibility(View.GONE);
                if (response.isSuccessful() && response.body() != null) {
                    showDevice(response.body());
                } else {
                    showError(ApiError.from(response));
                }
            }

            // Runs when the server could not be reached.
            @Override
            public void onFailure(@NonNull Call<ApiModels.Device> call, @NonNull Throwable t) {
                if (isDestroyed()) return;
                progressBar.setVisibility(View.GONE);
                Toast.makeText(DeviceActivity.this, R.string.network_error, Toast.LENGTH_LONG).show();
            }
        });
    }

    // Asks the backend again whether the admin approved this phone.
    private void checkStatus() {
        progressBar.setVisibility(View.VISIBLE);
        ApiClient.get(this).myDevices().enqueue(new Callback<List<ApiModels.Device>>() {
            // Runs when the server answers.
            @Override
            public void onResponse(@NonNull Call<List<ApiModels.Device>> call, @NonNull Response<List<ApiModels.Device>> response) {
                if (isDestroyed()) return;
                progressBar.setVisibility(View.GONE);
                if (!response.isSuccessful() || response.body() == null) {
                    showError(ApiError.from(response));
                    return;
                }
                for (ApiModels.Device device : response.body()) {
                    if (deviceId.equals(device.deviceId)) {
                        showDevice(device);
                        return;
                    }
                }
                registerPhone();
            }

            // Runs when the server could not be reached.
            @Override
            public void onFailure(@NonNull Call<List<ApiModels.Device>> call, @NonNull Throwable t) {
                if (isDestroyed()) return;
                progressBar.setVisibility(View.GONE);
                Toast.makeText(DeviceActivity.this, R.string.network_error, Toast.LENGTH_LONG).show();
            }
        });
    }

    // Opens the exam list when approved, otherwise shows the waiting message.
    private void showDevice(ApiModels.Device device) {
        if ("approved".equals(device.status)) {
            startActivity(new Intent(this, ExamListActivity.class));
            finish();
            return;
        }
        statusText.setText(R.string.device_pending);
        noteText.setVisibility(View.VISIBLE);
    }

    // Sends the user to login when the session expired, otherwise shows the server message.
    private void showError(ApiError error) {
        if (error.sessionExpired()) {
            AppUtils.logoutToLogin(this);
            return;
        }
        Toast.makeText(this, error.message, Toast.LENGTH_LONG).show();
    }
}
