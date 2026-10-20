package com.parallaxlane.app.api;

import com.parallaxlane.app.model.ApiModels;

import java.util.List;

import retrofit2.Call;
import retrofit2.http.Body;
import retrofit2.http.GET;
import retrofit2.http.POST;
import retrofit2.http.Path;
import retrofit2.http.Query;

// The backend endpoints the app uses, Retrofit turns each method into an HTTP request.
public interface ApiService {

    // Signs in with email and password, returns tokens.
    @POST("login/")
    Call<ApiModels.LoginResponse> login(@Body ApiModels.LoginRequest body);

    // Gets a new access token using the refresh token.
    @POST("token/refresh/")
    Call<ApiModels.RefreshResponse> refresh(@Body ApiModels.RefreshRequest body);

    // Cancels the refresh token on the server.
    @POST("accounts/logout/")
    Call<ApiModels.StatusResponse> logout(@Body ApiModels.RefreshRequest body);

    // Registers this phone, returns approved or pending.
    @POST("accounts/devices/register/")
    Call<ApiModels.Device> registerDevice(@Body ApiModels.DeviceRequest body);

    // Lists the phones of this account to check approval.
    @GET("accounts/devices/me/")
    Call<List<ApiModels.Device>> myDevices();

    // Joins a college using the code given by the teacher.
    @POST("organisations/join-by-code/")
    Call<ApiModels.JoinResponse> joinByCode(@Body ApiModels.CodeRequest body);

    // Lists the exams of the current college.
    @GET("exams/")
    Call<ApiModels.ExamPage> getExams(@Query("page") int page);

    // Gets an exam, questions come only after the attempt starts.
    @GET("exams/{id}/")
    Call<ApiModels.ExamDetail> getExamDetail(@Path("id") long examId);

    // Gets the one time text the phone must sign before starting.
    @POST("exams/{id}/challenge/")
    Call<ApiModels.Challenge> getChallenge(@Path("id") long examId);

    // Starts or resumes the attempt, returns the deadline.
    @POST("exams/{id}/start/")
    Call<ApiModels.StartResponse> startExam(@Path("id") long examId, @Body ApiModels.StartRequest body);

    // Saves one answer as soon as it is chosen.
    @POST("exams/answers/save/")
    Call<ApiModels.StatusResponse> saveAnswer(@Body ApiModels.AnswerRequest body);

    // Submits the exam and returns the score.
    @POST("exams/{id}/submit/")
    Call<ApiModels.SubmitResponse> submitExam(@Path("id") long examId, @Body ApiModels.SubmitRequest body);

    // Lists the scores of finished exams.
    @GET("exams/my-results/")
    Call<List<ApiModels.Result>> getResults();

    // Tells the server the exam screen is still open.
    @POST("monitoring/heartbeat/")
    Call<ApiModels.AttemptState> heartbeat(@Body ApiModels.HeartbeatRequest body);

    // Reports that the student left the exam.
    @POST("monitoring/log/")
    Call<ApiModels.AttemptState> reportViolation(@Body ApiModels.ViolationRequest body);
}
