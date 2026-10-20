package com.parallaxlane.app.ui;

import android.content.Intent;
import android.os.Bundle;
import android.widget.Button;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

import com.parallaxlane.app.R;

// Shows the score right after the student submits an exam.
public class ResultActivity extends AppCompatActivity {

    // Reads the score passed by the exam screen and shows it.
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_result);
        setTitle(R.string.result_title);

        TextView examTitleText = findViewById(R.id.examTitleText);
        TextView scoreText = findViewById(R.id.scoreText);
        TextView reasonText = findViewById(R.id.reasonText);
        Button backButton = findViewById(R.id.backButton);

        double points = getIntent().getDoubleExtra("points", 0);
        double total = getIntent().getDoubleExtra("total", 0);
        examTitleText.setText(getIntent().getStringExtra("exam_title"));
        scoreText.setText(getString(R.string.score, formatNumber(points), formatNumber(total)));
        reasonText.setText(reasonMessage(getIntent().getStringExtra("reason")));

        backButton.setOnClickListener(v -> {
            Intent intent = new Intent(this, ExamListActivity.class);
            intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
            startActivity(intent);
            finish();
        });
    }

    // Shows 8 instead of 8.0 when the score has no decimal part.
    static String formatNumber(double value) {
        return value == Math.floor(value) ? String.valueOf((long) value) : String.valueOf(value);
    }

    // Turns the end reason code from the backend into a sentence.
    static String reasonMessage(String reason) {
        if ("submitted".equals(reason)) {
            return "You submitted the exam.";
        } else if ("deadline_expired".equals(reason)) {
            return "Time ran out, the answers you had saved were submitted.";
        } else if ("violation_threshold".equals(reason)) {
            return "The exam was ended because of too many warnings.";
        } else if ("exam_disabled_by_admin".equals(reason)) {
            return "The exam was closed by the examiner.";
        }
        return "";
    }
}
