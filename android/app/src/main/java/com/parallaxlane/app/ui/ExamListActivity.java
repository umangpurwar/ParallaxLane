package com.parallaxlane.app.ui;

import android.content.Intent;
import android.os.Bundle;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;

import com.parallaxlane.app.R;
import com.parallaxlane.app.api.ApiClient;
import com.parallaxlane.app.api.ApiError;
import com.parallaxlane.app.model.ApiModels;
import com.parallaxlane.app.util.AppUtils;
import com.parallaxlane.app.util.DeviceHelper;
import com.parallaxlane.app.util.SessionManager;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

// Shows the exams of the student's college and starts an exam when one is chosen.
public class ExamListActivity extends AppCompatActivity {

    private SwipeRefreshLayout swipeRefresh;
    private TextView emptyText;
    private ExamAdapter adapter;
    private SessionManager session;

    // Sets up the list, the pull to refresh and loads the exams.
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_exam_list);
        setTitle(R.string.exams_title);
        session = new SessionManager(this);
        if (getSupportActionBar() != null) {
            getSupportActionBar().setSubtitle(session.getOrgName());
        }
        swipeRefresh = findViewById(R.id.swipeRefresh);
        emptyText = findViewById(R.id.emptyText);
        RecyclerView recycler = findViewById(R.id.examRecycler);
        recycler.setLayoutManager(new LinearLayoutManager(this));
        adapter = new ExamAdapter(this::confirmStart);
        recycler.setAdapter(adapter);
        swipeRefresh.setColorSchemeResources(R.color.black);
        swipeRefresh.setOnRefreshListener(this::loadExams);
        loadExams();
    }

    // Gets the exam list from the backend.
    private void loadExams() {
        swipeRefresh.setRefreshing(true);
        ApiClient.get(this).getExams(1).enqueue(new Callback<ApiModels.ExamPage>() {
            // Runs when the server answers.
            @Override
            public void onResponse(@NonNull Call<ApiModels.ExamPage> call, @NonNull Response<ApiModels.ExamPage> response) {
                if (isDestroyed()) return;
                swipeRefresh.setRefreshing(false);
                if (response.isSuccessful() && response.body() != null) {
                    adapter.setExams(response.body().results);
                    emptyText.setVisibility(response.body().results.isEmpty() ? View.VISIBLE : View.GONE);
                } else {
                    showError(ApiError.from(response));
                }
            }

            // Runs when the server could not be reached.
            @Override
            public void onFailure(@NonNull Call<ApiModels.ExamPage> call, @NonNull Throwable t) {
                if (isDestroyed()) return;
                swipeRefresh.setRefreshing(false);
                Toast.makeText(ExamListActivity.this, R.string.network_error, Toast.LENGTH_LONG).show();
            }
        });
    }

    // Shows the exam rules and asks the student to confirm before starting.
    private void confirmStart(ApiModels.Exam exam) {
        if (!"Open now".equals(AppUtils.examStatus(exam))) {
            Toast.makeText(this, "This exam is " + AppUtils.examStatus(exam).toLowerCase(), Toast.LENGTH_SHORT).show();
            return;
        }
        new AlertDialog.Builder(this)
                .setTitle(exam.title)
                .setMessage(getString(R.string.start_rules, exam.duration))
                .setPositiveButton(R.string.start_exam, (dialog, which) -> requestChallenge(exam))
                .setNegativeButton(R.string.cancel, null)
                .show();
    }

    // Step one of starting: asks the backend for a one time text to sign.
    private void requestChallenge(ApiModels.Exam exam) {
        ApiClient.get(this).getChallenge(exam.id).enqueue(new Callback<ApiModels.Challenge>() {
            // Runs when the server answers.
            @Override
            public void onResponse(@NonNull Call<ApiModels.Challenge> call, @NonNull Response<ApiModels.Challenge> response) {
                if (isDestroyed()) return;
                if (response.isSuccessful() && response.body() != null) {
                    startExam(exam, response.body());
                } else {
                    showError(ApiError.from(response));
                }
            }

            // Runs when the server could not be reached.
            @Override
            public void onFailure(@NonNull Call<ApiModels.Challenge> call, @NonNull Throwable t) {
                if (isDestroyed()) return;
                Toast.makeText(ExamListActivity.this, R.string.network_error, Toast.LENGTH_LONG).show();
            }
        });
    }

    // Step two of starting: signs the text with the phone key and starts the attempt.
    private void startExam(ApiModels.Exam exam, ApiModels.Challenge challenge) {
        String signature;
        try {
            signature = DeviceHelper.sign(challenge.signPayload);
        } catch (Exception e) {
            Toast.makeText(this, "Could not sign the request on this phone", Toast.LENGTH_LONG).show();
            return;
        }
        ApiModels.StartRequest request = new ApiModels.StartRequest(challenge.nonce, signature);
        ApiClient.get(this).startExam(exam.id, request).enqueue(new Callback<ApiModels.StartResponse>() {
            // Runs when the server answers.
            @Override
            public void onResponse(@NonNull Call<ApiModels.StartResponse> call, @NonNull Response<ApiModels.StartResponse> response) {
                if (isDestroyed()) return;
                if (response.isSuccessful() && response.body() != null) {
                    openExam(exam, response.body());
                } else {
                    showError(ApiError.from(response));
                }
            }

            // Runs when the server could not be reached.
            @Override
            public void onFailure(@NonNull Call<ApiModels.StartResponse> call, @NonNull Throwable t) {
                if (isDestroyed()) return;
                Toast.makeText(ExamListActivity.this, R.string.network_error, Toast.LENGTH_LONG).show();
            }
        });
    }

    // Opens the exam screen and passes the attempt details to it.
    private void openExam(ApiModels.Exam exam, ApiModels.StartResponse attempt) {
        Intent intent = new Intent(this, ExamActivity.class);
        intent.putExtra("exam_id", exam.id);
        intent.putExtra("exam_title", exam.title);
        intent.putExtra("attempt_id", attempt.attemptId);
        intent.putExtra("time_left_ms", AppUtils.millisBetween(attempt.serverTime, attempt.deadline));
        startActivity(intent);
    }

    // Shows a dialog where the student types the join code given by the college.
    private void showJoinDialog() {
        EditText codeInput = new EditText(this);
        codeInput.setHint("Code");
        int padding = (int) (20 * getResources().getDisplayMetrics().density);
        codeInput.setPadding(padding, padding, padding, padding);
        new AlertDialog.Builder(this)
                .setTitle(R.string.join_with_code)
                .setView(codeInput)
                .setPositiveButton(R.string.join, (dialog, which) -> joinWithCode(codeInput.getText().toString().trim()))
                .setNegativeButton(R.string.cancel, null)
                .show();
    }

    // Sends the join code to the backend and reloads the exams.
    private void joinWithCode(String code) {
        ApiClient.get(this).joinByCode(new ApiModels.CodeRequest(code)).enqueue(new Callback<ApiModels.JoinResponse>() {
            // Runs when the server answers.
            @Override
            public void onResponse(@NonNull Call<ApiModels.JoinResponse> call, @NonNull Response<ApiModels.JoinResponse> response) {
                if (isDestroyed()) return;
                if (response.isSuccessful() && response.body() != null) {
                    session.saveOrgName(response.body().organisationName);
                    if (getSupportActionBar() != null) {
                        getSupportActionBar().setSubtitle(response.body().organisationName);
                    }
                    loadExams();
                } else {
                    showError(ApiError.from(response));
                }
            }

            // Runs when the server could not be reached.
            @Override
            public void onFailure(@NonNull Call<ApiModels.JoinResponse> call, @NonNull Throwable t) {
                if (isDestroyed()) return;
                Toast.makeText(ExamListActivity.this, R.string.network_error, Toast.LENGTH_LONG).show();
            }
        });
    }

    // Tells the backend to cancel the refresh token, then clears the session once the server has answered.
    private void signOut() {
        String refresh = session.getRefreshToken();
        if (refresh == null) {
            AppUtils.logoutToLogin(this);
            return;
        }
        swipeRefresh.setRefreshing(true);
        ApiClient.get(this).logout(new ApiModels.RefreshRequest(refresh)).enqueue(new Callback<ApiModels.StatusResponse>() {
            // Runs when the server answers.
            @Override
            public void onResponse(@NonNull Call<ApiModels.StatusResponse> call, @NonNull Response<ApiModels.StatusResponse> response) {
                if (!isDestroyed()) AppUtils.logoutToLogin(ExamListActivity.this);
            }

            // Runs when the server could not be reached.
            @Override
            public void onFailure(@NonNull Call<ApiModels.StatusResponse> call, @NonNull Throwable t) {
                if (!isDestroyed()) AppUtils.logoutToLogin(ExamListActivity.this);
            }
        });
    }

    // Sends the user to login when the session expired, otherwise shows the server message.
    private void showError(ApiError error) {
        if (error.sessionExpired()) {
            AppUtils.logoutToLogin(this);
            return;
        }
        Toast.makeText(this, error.message, Toast.LENGTH_LONG).show();
    }

    // Adds the Results, Join with code and Sign out menu items.
    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        getMenuInflater().inflate(R.menu.menu_exam_list, menu);
        return true;
    }

    // Handles a tap on one of the menu items.
    @Override
    public boolean onOptionsItemSelected(@NonNull MenuItem item) {
        if (item.getItemId() == R.id.menuResults) {
            startActivity(new Intent(this, ResultsActivity.class));
            return true;
        } else if (item.getItemId() == R.id.menuJoin) {
            showJoinDialog();
            return true;
        } else if (item.getItemId() == R.id.menuSignOut) {
            signOut();
            return true;
        }
        return super.onOptionsItemSelected(item);
    }
}
