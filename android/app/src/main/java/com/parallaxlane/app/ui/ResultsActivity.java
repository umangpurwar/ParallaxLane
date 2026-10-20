package com.parallaxlane.app.ui;

import android.os.Bundle;
import android.widget.ArrayAdapter;
import android.widget.ListView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;

import com.parallaxlane.app.R;
import com.parallaxlane.app.api.ApiClient;
import com.parallaxlane.app.api.ApiError;
import com.parallaxlane.app.model.ApiModels;
import com.parallaxlane.app.util.AppUtils;

import java.util.ArrayList;
import java.util.List;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

// Lists all finished exams of the student with their scores.
public class ResultsActivity extends AppCompatActivity {

    private final List<String> rows = new ArrayList<>();
    private ArrayAdapter<String> adapter;

    // Sets up a simple ListView and loads the results.
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_results);
        ListView listView = findViewById(R.id.resultsList);
        adapter = new ArrayAdapter<>(this, android.R.layout.simple_list_item_1, rows);
        listView.setAdapter(adapter);
        loadResults();
    }

    // Gets the results from the backend and shows one line per exam.
    private void loadResults() {
        ApiClient.get(this).getResults().enqueue(new Callback<List<ApiModels.Result>>() {
            // Runs when the server answers.
            @Override
            public void onResponse(@NonNull Call<List<ApiModels.Result>> call, @NonNull Response<List<ApiModels.Result>> response) {
                if (isDestroyed()) return;
                if (!response.isSuccessful() || response.body() == null) {
                    Toast.makeText(ResultsActivity.this, ApiError.from(response).message, Toast.LENGTH_LONG).show();
                    return;
                }
                rows.clear();
                for (ApiModels.Result result : response.body()) {
                    rows.add(result.examTitle + "\n"
                            + ResultActivity.formatNumber(result.pointsScored) + " / " + ResultActivity.formatNumber(result.totalPoints)
                            + ", " + result.state + ", " + AppUtils.formatTime(result.date) + "\n"
                            + ResultActivity.reasonMessage(result.endReason));
                }
                if (rows.isEmpty()) {
                    rows.add("No results yet");
                }
                adapter.notifyDataSetChanged();
            }

            // Runs when the server could not be reached.
            @Override
            public void onFailure(@NonNull Call<List<ApiModels.Result>> call, @NonNull Throwable t) {
                if (isDestroyed()) return;
                Toast.makeText(ResultsActivity.this, R.string.network_error, Toast.LENGTH_LONG).show();
            }
        });
    }
}
