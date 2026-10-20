package com.parallaxlane.app.util;

import android.app.Activity;
import android.content.Intent;

import com.parallaxlane.app.model.ApiModels;
import com.parallaxlane.app.ui.LoginActivity;

import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;

// Small helper methods shared by more than one screen.
public class AppUtils {

    private static final DateTimeFormatter DISPLAY_FORMAT = DateTimeFormatter.ofPattern("dd MMM, hh:mm a");

    // Turns a date sent by the server in ISO format into readable local time.
    public static String formatTime(String isoTime) {
        if (isoTime == null) {
            return "";
        }
        return OffsetDateTime.parse(isoTime).atZoneSameInstant(ZoneId.systemDefault()).format(DISPLAY_FORMAT);
    }

    // Returns the milliseconds between two server times, used to start the exam timer.
    public static long millisBetween(String fromIso, String toIso) {
        return java.time.Duration.between(OffsetDateTime.parse(fromIso), OffsetDateTime.parse(toIso)).toMillis();
    }

    // Tells whether the exam can be started now based on its start and end time.
    public static String examStatus(ApiModels.Exam exam) {
        OffsetDateTime now = OffsetDateTime.now();
        if (!exam.isActive) {
            return "Closed";
        }
        if (now.isBefore(OffsetDateTime.parse(exam.startTime))) {
            return "Upcoming";
        }
        if (now.isAfter(OffsetDateTime.parse(exam.endTime))) {
            return "Closed";
        }
        return "Open now";
    }

    // Clears the session and opens the login screen with no screens left behind it.
    public static void logoutToLogin(Activity activity) {
        new SessionManager(activity).clear();
        Intent intent = new Intent(activity, LoginActivity.class);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
        activity.startActivity(intent);
        activity.finish();
    }
}
