package com.parallaxlane.app.ui;

import android.app.ActivityManager;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.os.CountDownTimer;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.RadioButton;
import android.widget.RadioGroup;
import android.widget.TextView;
import android.widget.Toast;

import androidx.activity.OnBackPressedCallback;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;

import com.bumptech.glide.Glide;
import com.parallaxlane.app.R;
import com.parallaxlane.app.api.ApiClient;
import com.parallaxlane.app.api.ApiError;
import com.parallaxlane.app.api.ApiService;
import com.parallaxlane.app.model.ApiModels;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

// The exam screen: shows one question at a time, saves answers, runs the timer, sends heartbeats and reports leaving the app.
public class ExamActivity extends AppCompatActivity {

    private static final long HEARTBEAT_INTERVAL_MS = 10000;

    private TextView timerText;
    private TextView counterText;
    private TextView questionText;
    private TextView saveStatusText;
    private ImageView questionImage;
    private RadioGroup optionsGroup;
    private EditText answerInput;
    private Button prevButton;
    private Button nextButton;

    private ApiService api;
    private long examId;
    private long attemptId;
    private String examTitle;
    private List<ApiModels.Question> questions = new ArrayList<>();
    private final Map<Long, Object> answers = new HashMap<>();
    private int currentIndex = 0;

    private CountDownTimer timer;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private boolean examOver = false;
    private boolean wasPinned = false;

    // Blocks screenshots, reads the attempt details, pins the screen and loads the questions.
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE);
        setContentView(R.layout.activity_exam);
        if (getSupportActionBar() != null) {
            getSupportActionBar().hide();
        }

        api = ApiClient.get(this);
        examId = getIntent().getLongExtra("exam_id", 0);
        attemptId = getIntent().getLongExtra("attempt_id", 0);
        examTitle = getIntent().getStringExtra("exam_title");
        long timeLeftMs = getIntent().getLongExtra("time_left_ms", 0);

        timerText = findViewById(R.id.timerText);
        counterText = findViewById(R.id.counterText);
        questionText = findViewById(R.id.questionText);
        saveStatusText = findViewById(R.id.saveStatusText);
        questionImage = findViewById(R.id.questionImage);
        optionsGroup = findViewById(R.id.optionsGroup);
        answerInput = findViewById(R.id.answerInput);
        prevButton = findViewById(R.id.prevButton);
        nextButton = findViewById(R.id.nextButton);

        prevButton.setOnClickListener(v -> goToQuestion(currentIndex - 1));
        nextButton.setOnClickListener(v -> onNextPressed());

        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            // Blocks the back button while the exam is running.
            @Override
            public void handleOnBackPressed() {
                Toast.makeText(ExamActivity.this, R.string.back_blocked, Toast.LENGTH_SHORT).show();
            }
        });

        try {
            startLockTask();
        } catch (Exception e) {
            Toast.makeText(this, "Turn on App pinning in Settings to take exams", Toast.LENGTH_LONG).show();
        }

        startTimer(timeLeftMs);
        handler.postDelayed(heartbeatTask, HEARTBEAT_INTERVAL_MS);
        loadQuestions();
    }

    // Downloads the questions of this attempt from the backend.
    private void loadQuestions() {
        api.getExamDetail(examId).enqueue(new Callback<ApiModels.ExamDetail>() {
            // Runs when the server answers.
            @Override
            public void onResponse(@NonNull Call<ApiModels.ExamDetail> call, @NonNull Response<ApiModels.ExamDetail> response) {
                if (isDestroyed()) return;
                if (response.isSuccessful() && response.body() != null && response.body().questions != null) {
                    questions = response.body().questions;
                    goToQuestion(0);
                } else {
                    Toast.makeText(ExamActivity.this, "Could not load the questions", Toast.LENGTH_LONG).show();
                }
            }

            // Runs when the server could not be reached.
            @Override
            public void onFailure(@NonNull Call<ApiModels.ExamDetail> call, @NonNull Throwable t) {
                if (isDestroyed()) return;
                Toast.makeText(ExamActivity.this, R.string.network_error, Toast.LENGTH_LONG).show();
            }
        });
    }

    // Shows the question at the given position with its options or a text box.
    private void goToQuestion(int index) {
        if (index < 0 || index >= questions.size()) {
            return;
        }
        saveTypedAnswer();
        currentIndex = index;
        ApiModels.Question question = questions.get(index);

        counterText.setText(String.format(Locale.getDefault(), "Question %d of %d", index + 1, questions.size()));
        questionText.setText(question.text);
        saveStatusText.setText(answers.containsKey(question.id) ? getString(R.string.saved) : "");
        prevButton.setEnabled(index > 0);
        nextButton.setText(index == questions.size() - 1 ? R.string.submit : R.string.next);

        if (question.image != null && !question.image.isEmpty()) {
            questionImage.setVisibility(View.VISIBLE);
            Glide.with(this).load(question.image).into(questionImage);
        } else {
            questionImage.setVisibility(View.GONE);
        }

        optionsGroup.setOnCheckedChangeListener(null);
        optionsGroup.removeAllViews();
        if ("short_answer".equals(question.questionType)) {
            optionsGroup.setVisibility(View.GONE);
            answerInput.setVisibility(View.VISIBLE);
            Object saved = answers.get(question.id);
            answerInput.setText(saved == null ? "" : saved.toString());
        } else {
            answerInput.setVisibility(View.GONE);
            optionsGroup.setVisibility(View.VISIBLE);
            for (ApiModels.Option option : question.options) {
                RadioButton radio = new RadioButton(this);
                radio.setId(View.generateViewId());
                radio.setText(option.text);
                radio.setTextSize(16);
                radio.setMinHeight((int) (48 * getResources().getDisplayMetrics().density));
                radio.setTag(option.id);
                optionsGroup.addView(radio);
                if (Long.valueOf(option.id).equals(answers.get(question.id))) {
                    radio.setChecked(true);
                }
            }
            optionsGroup.setOnCheckedChangeListener((group, checkedId) -> {
                RadioButton chosen = group.findViewById(checkedId);
                if (chosen != null) {
                    saveAnswer(question.id, (Long) chosen.getTag());
                }
            });
        }
    }

    // Moves to the next question, or asks to submit on the last one.
    private void onNextPressed() {
        if (currentIndex == questions.size() - 1) {
            saveTypedAnswer();
            new AlertDialog.Builder(this)
                    .setMessage(R.string.submit_confirm)
                    .setPositiveButton(R.string.submit, (dialog, which) -> submitExam())
                    .setNegativeButton(R.string.cancel, null)
                    .show();
        } else {
            goToQuestion(currentIndex + 1);
        }
    }

    // Saves the text of a short answer question when the student leaves it.
    private void saveTypedAnswer() {
        if (questions.isEmpty() || answerInput.getVisibility() != View.VISIBLE) {
            return;
        }
        ApiModels.Question question = questions.get(currentIndex);
        String text = answerInput.getText().toString().trim();
        if (!text.isEmpty() && !text.equals(answers.get(question.id))) {
            saveAnswer(question.id, text);
        }
    }

    // Keeps the answer in memory and sends it to the backend at once.
    private void saveAnswer(long questionId, Object value) {
        answers.put(questionId, value);
        saveStatusText.setText(R.string.saving);
        api.saveAnswer(new ApiModels.AnswerRequest(attemptId, questionId, value)).enqueue(new Callback<ApiModels.StatusResponse>() {
            // Runs when the server answers.
            @Override
            public void onResponse(@NonNull Call<ApiModels.StatusResponse> call, @NonNull Response<ApiModels.StatusResponse> response) {
                if (isDestroyed()) return;
                if (response.isSuccessful()) {
                    saveStatusText.setText(R.string.saved);
                    return;
                }
                ApiError error = ApiError.from(response);
                if (error.attemptEnded()) {
                    endedByServer();
                } else {
                    saveStatusText.setText(R.string.not_saved);
                }
            }

            // Runs when the server could not be reached.
            @Override
            public void onFailure(@NonNull Call<ApiModels.StatusResponse> call, @NonNull Throwable t) {
                if (isDestroyed()) return;
                saveStatusText.setText(R.string.not_saved);
            }
        });
    }

    // Sends every answer to the backend and opens the result screen.
    private void submitExam() {
        if (examOver) {
            return;
        }
        examOver = true;
        Map<String, Object> body = new HashMap<>();
        for (Map.Entry<Long, Object> entry : answers.entrySet()) {
            body.put(String.valueOf(entry.getKey()), entry.getValue());
        }
        api.submitExam(examId, new ApiModels.SubmitRequest(body)).enqueue(new Callback<ApiModels.SubmitResponse>() {
            // Runs when the server answers.
            @Override
            public void onResponse(@NonNull Call<ApiModels.SubmitResponse> call, @NonNull Response<ApiModels.SubmitResponse> response) {
                if (isDestroyed()) return;
                if (response.isSuccessful() && response.body() != null) {
                    openResult(response.body());
                } else if (ApiError.from(response).attemptEnded()) {
                    endedByServer();
                } else {
                    showSubmitRetry();
                }
            }

            // Runs when the server could not be reached.
            @Override
            public void onFailure(@NonNull Call<ApiModels.SubmitResponse> call, @NonNull Throwable t) {
                if (isDestroyed()) return;
                showSubmitRetry();
            }
        });
    }

    // Lets the student try the submit again when the network failed.
    private void showSubmitRetry() {
        examOver = false;
        handler.removeCallbacks(heartbeatTask);
        handler.postDelayed(heartbeatTask, HEARTBEAT_INTERVAL_MS);
        new AlertDialog.Builder(this)
                .setMessage(R.string.network_error)
                .setCancelable(false)
                .setPositiveButton(R.string.retry, (dialog, which) -> submitExam())
                .show();
    }

    // Starts the countdown from the time the server gave, submits when it reaches zero.
    private void startTimer(long timeLeftMs) {
        timer = new CountDownTimer(timeLeftMs, 1000) {
            // Updates the timer text every second.
            @Override
            public void onTick(long millisLeft) {
                long seconds = millisLeft / 1000;
                timerText.setText(String.format(Locale.getDefault(), "%02d:%02d", seconds / 60, seconds % 60));
            }

            // Submits the exam when the time is up.
            @Override
            public void onFinish() {
                timerText.setText("00:00");
                saveTypedAnswer();
                submitExam();
            }
        };
        timer.start();
    }

    // Runs every ten seconds, tells the backend the exam screen is still open and checks screen pinning.
    private final Runnable heartbeatTask = new Runnable() {
        // Sends one heartbeat and schedules the next one.
        @Override
        public void run() {
            if (examOver) {
                return;
            }
            boolean pinned = isScreenPinned();
            if (wasPinned && !pinned) {
                reportViolation("lock_task_exited");
            }
            wasPinned = pinned;
            ApiModels.PhoneState state = new ApiModels.PhoneState(hasWindowFocus(), pinned, isInMultiWindowMode());
            api.heartbeat(new ApiModels.HeartbeatRequest(attemptId, state)).enqueue(new Callback<ApiModels.AttemptState>() {
                // Runs when the server answers.
                @Override
                public void onResponse(@NonNull Call<ApiModels.AttemptState> call, @NonNull Response<ApiModels.AttemptState> response) {
                    if (isDestroyed()) return;
                    if (!response.isSuccessful() && ApiError.from(response).attemptEnded()) {
                        endedByServer();
                    }
                }

                // Runs when the server could not be reached.
                @Override
                public void onFailure(@NonNull Call<ApiModels.AttemptState> call, @NonNull Throwable t) {
                }
            });
            handler.postDelayed(this, HEARTBEAT_INTERVAL_MS);
        }
    };

    // Tells the backend the student left the exam and shows a warning, the backend decides when the exam ends.
    private void reportViolation(String type) {
        if (examOver) {
            return;
        }
        api.reportViolation(new ApiModels.ViolationRequest(attemptId, type)).enqueue(new Callback<ApiModels.AttemptState>() {
            // Runs when the server answers.
            @Override
            public void onResponse(@NonNull Call<ApiModels.AttemptState> call, @NonNull Response<ApiModels.AttemptState> response) {
                if (isDestroyed() || examOver) return;
                if (!response.isSuccessful()) {
                    if (ApiError.from(response).attemptEnded()) {
                        endedByServer();
                    }
                    return;
                }
                ApiModels.AttemptState state = response.body();
                if (state != null && "terminated".equals(state.state)) {
                    endedByServer();
                } else if (state != null) {
                    new AlertDialog.Builder(ExamActivity.this)
                            .setTitle(R.string.warning_title)
                            .setMessage(getString(R.string.warning_message, state.violations))
                            .setPositiveButton(android.R.string.ok, null)
                            .show();
                }
            }

            // Runs when the server could not be reached.
            @Override
            public void onFailure(@NonNull Call<ApiModels.AttemptState> call, @NonNull Throwable t) {
            }
        });
    }

    // Checks whether the screen is still pinned to this app.
    private boolean isScreenPinned() {
        ActivityManager manager = (ActivityManager) getSystemService(Context.ACTIVITY_SERVICE);
        return manager.getLockTaskModeState() != ActivityManager.LOCK_TASK_MODE_NONE;
    }

    // Called when the app goes to the background, counts as leaving the exam.
    @Override
    protected void onStop() {
        super.onStop();
        if (!examOver && !isFinishing()) {
            reportViolation("app_backgrounded");
        }
    }

    // Called when the student opens split screen, counts as a violation.
    @Override
    public void onMultiWindowModeChanged(boolean isInMultiWindowMode) {
        super.onMultiWindowModeChanged(isInMultiWindowMode);
        if (isInMultiWindowMode) {
            reportViolation("multi_window");
        }
    }

    // The backend already ended this attempt, so the student is sent to the results list.
    private void endedByServer() {
        if (isFinishing()) {
            return;
        }
        examOver = true;
        Toast.makeText(this, "Your exam has ended", Toast.LENGTH_LONG).show();
        stopExam();
        startActivity(new Intent(this, ResultsActivity.class));
        finish();
    }

    // Opens the result screen with the score from the submit response.
    private void openResult(ApiModels.SubmitResponse result) {
        stopExam();
        Intent intent = new Intent(this, ResultActivity.class);
        intent.putExtra("exam_title", examTitle);
        intent.putExtra("points", result.pointsScored);
        intent.putExtra("total", result.totalPoints);
        intent.putExtra("reason", result.endReason);
        startActivity(intent);
        finish();
    }

    // Stops the timer, the heartbeat and the screen pinning.
    private void stopExam() {
        if (timer != null) {
            timer.cancel();
        }
        handler.removeCallbacks(heartbeatTask);
        try {
            stopLockTask();
        } catch (Exception ignored) {
            // The screen was not pinned, nothing to stop.
        }
    }

    // Makes sure nothing keeps running after the screen is closed.
    @Override
    protected void onDestroy() {
        stopExam();
        super.onDestroy();
    }
}
