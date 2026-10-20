package com.parallaxlane.app.ui;

import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import com.parallaxlane.app.R;
import com.parallaxlane.app.model.ApiModels;
import com.parallaxlane.app.util.AppUtils;

import java.util.ArrayList;
import java.util.List;

// RecyclerView adapter that shows one row per exam.
public class ExamAdapter extends RecyclerView.Adapter<ExamAdapter.ExamViewHolder> {

    // Called when the student taps an exam.
    public interface OnExamClickListener {
        // Receives the exam that was tapped.
        void onExamClick(ApiModels.Exam exam);
    }

    private final List<ApiModels.Exam> exams = new ArrayList<>();
    private final OnExamClickListener listener;

    // Takes the click listener of the exam list screen.
    public ExamAdapter(OnExamClickListener listener) {
        this.listener = listener;
    }

    // Replaces the list with new exams from the server.
    public void setExams(List<ApiModels.Exam> newExams) {
        exams.clear();
        exams.addAll(newExams);
        notifyDataSetChanged();
    }

    // Creates one row view from the item exam layout file.
    @NonNull
    @Override
    public ExamViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_exam, parent, false);
        return new ExamViewHolder(view);
    }

    // Fills one row with the exam title, time and status.
    @Override
    public void onBindViewHolder(@NonNull ExamViewHolder holder, int position) {
        ApiModels.Exam exam = exams.get(position);
        holder.titleText.setText(exam.title);
        holder.timeText.setText(exam.duration + " min, " + AppUtils.formatTime(exam.startTime) + " to " + AppUtils.formatTime(exam.endTime));
        holder.statusText.setText(AppUtils.examStatus(exam));
        holder.itemView.setOnClickListener(v -> listener.onExamClick(exam));
    }

    // Returns how many exams are in the list.
    @Override
    public int getItemCount() {
        return exams.size();
    }

    // Holds the views of one row so they are not searched again on scroll.
    static class ExamViewHolder extends RecyclerView.ViewHolder {
        final TextView titleText;
        final TextView timeText;
        final TextView statusText;

        // Finds the views of one row.
        ExamViewHolder(View itemView) {
            super(itemView);
            titleText = itemView.findViewById(R.id.titleText);
            timeText = itemView.findViewById(R.id.timeText);
            statusText = itemView.findViewById(R.id.statusText);
        }
    }
}
