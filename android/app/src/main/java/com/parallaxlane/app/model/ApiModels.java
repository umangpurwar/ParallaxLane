package com.parallaxlane.app.model;

import java.util.List;
import java.util.Map;

// All request and response classes for the backend API, Gson fills these fields from the JSON the server sends.
public class ApiModels {

    // Sent to the login endpoint.
    public static class LoginRequest {
        String email;
        String password;

        // Fills the fields of this request before it is sent.
        public LoginRequest(String email, String password) {
            this.email = email;
            this.password = password;
        }
    }

    // Returned by the login endpoint.
    public static class LoginResponse {
        public String access;
        public String refresh;
        public String displayName;
        public String orgName;
    }

    // Sent to get a new access token, also sent when signing out.
    public static class RefreshRequest {
        String refresh;

        // Fills the fields of this request before it is sent.
        public RefreshRequest(String refresh) {
            this.refresh = refresh;
        }
    }

    // Returned when tokens are refreshed.
    public static class RefreshResponse {
        public String access;
        public String refresh;
    }

    // Sent to join a college or organisation with a code.
    public static class CodeRequest {
        String code;

        // Fills the fields of this request before it is sent.
        public CodeRequest(String code) {
            this.code = code;
        }
    }

    // Returned after joining with a code.
    public static class JoinResponse {
        public String organisationName;
    }

    // Sent to register this phone.
    public static class DeviceRequest {
        String deviceId;
        String publicKey;
        String modelName;

        // Fills the fields of this request before it is sent.
        public DeviceRequest(String deviceId, String publicKey, String modelName) {
            this.deviceId = deviceId;
            this.publicKey = publicKey;
            this.modelName = modelName;
        }
    }

    // One registered phone, status is approved or pending.
    public static class Device {
        public String deviceId;
        public String modelName;
        public String status;
        public String pendingReason;
    }

    // One page of exams.
    public static class ExamPage {
        public int count;
        public List<Exam> results;
    }

    // One exam in the list.
    public static class Exam {
        public long id;
        public String title;
        public String description;
        public int duration;
        public String startTime;
        public String endTime;
        public boolean isActive;
    }

    // Exam with its questions, questions is null until the attempt has started.
    public static class ExamDetail extends Exam {
        public List<Question> questions;
    }

    // One question, the correct answer is never sent to the phone.
    public static class Question {
        public long id;
        public String text;
        public String questionType;
        public int points;
        public String image;
        public List<Option> options;
    }

    // One answer choice.
    public static class Option {
        public long id;
        public String text;
    }

    // Returned before starting an exam, the phone signs signPayload.
    public static class Challenge {
        public String nonce;
        public String signPayload;
    }

    // Sent to start the exam with the signed challenge.
    public static class StartRequest {
        String nonce;
        String signature;

        // Fills the fields of this request before it is sent.
        public StartRequest(String nonce, String signature) {
            this.nonce = nonce;
            this.signature = signature;
        }
    }

    // Returned when the exam attempt starts.
    public static class StartResponse {
        public long attemptId;
        public String deadline;
        public String serverTime;
        public boolean resumed;
    }

    // Sent each time the student picks or types an answer.
    public static class AnswerRequest {
        long attemptId;
        long questionId;
        Object answer;

        // Fills the fields of this request before it is sent.
        public AnswerRequest(long attemptId, long questionId, Object answer) {
            this.attemptId = attemptId;
            this.questionId = questionId;
            this.answer = answer;
        }
    }

    // Sent at the end with every answer as a backup.
    public static class SubmitRequest {
        Map<String, Object> answers;

        // Fills the fields of this request before it is sent.
        public SubmitRequest(Map<String, Object> answers) {
            this.answers = answers;
        }
    }

    // Returned after submitting.
    public static class SubmitResponse {
        public String state;
        public String endReason;
        public double pointsScored;
        public double totalPoints;
        public int totalQuestions;
    }

    // One finished exam in the results list.
    public static class Result {
        public String examTitle;
        public double pointsScored;
        public double totalPoints;
        public int violations;
        public String state;
        public String endReason;
        public String date;
    }

    // What the phone reports every ten seconds during an exam.
    public static class PhoneState {
        boolean foreground;
        boolean lockTask;
        boolean multiWindow;

        // Fills the fields of this request before it is sent.
        public PhoneState(boolean foreground, boolean lockTask, boolean multiWindow) {
            this.foreground = foreground;
            this.lockTask = lockTask;
            this.multiWindow = multiWindow;
        }
    }

    // Sent every ten seconds during an exam.
    public static class HeartbeatRequest {
        long attemptId;
        PhoneState state;

        // Fills the fields of this request before it is sent.
        public HeartbeatRequest(long attemptId, PhoneState state) {
            this.attemptId = attemptId;
            this.state = state;
        }
    }

    // Sent when the app notices the student leaving the exam.
    public static class ViolationRequest {
        long attemptId;
        String type;

        // Fills the fields of this request before it is sent.
        public ViolationRequest(long attemptId, String type) {
            this.attemptId = attemptId;
            this.type = type;
        }
    }

    // Returned by heartbeat and violation calls, state active means the exam is still running.
    public static class AttemptState {
        public String state;
        public int violations;
        public String deadline;
        public String serverTime;
    }

    // Plain status reply.
    public static class StatusResponse {
        public String status;
    }
}
