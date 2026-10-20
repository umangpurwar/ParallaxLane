package com.parallaxlane.app.api;

import android.content.Context;

import androidx.annotation.NonNull;

import com.parallaxlane.app.BuildConfig;
import com.parallaxlane.app.util.DeviceHelper;
import com.parallaxlane.app.util.SessionManager;

import java.io.IOException;

import okhttp3.Interceptor;
import okhttp3.Request;
import okhttp3.Response;

// OkHttp interceptor that adds the headers the backend expects to every request.
public class HeaderInterceptor implements Interceptor {

    private final SessionManager session;
    private final String deviceId;
    private final boolean addToken;

    // Takes the session to read the token from and whether this client should send the token.
    public HeaderInterceptor(Context context, SessionManager session, boolean addToken) {
        this.session = session;
        this.deviceId = DeviceHelper.getDeviceId(context);
        this.addToken = addToken;
    }

    // Adds app version, device id and the login token, then sends the request on.
    @NonNull
    @Override
    public Response intercept(@NonNull Chain chain) throws IOException {
        Request.Builder builder = chain.request().newBuilder()
                .header("X-Client", "android")
                .header("X-App-Version", String.valueOf(BuildConfig.VERSION_CODE))
                .header("X-Device-Id", deviceId);
        String token = session.getAccessToken();
        if (addToken && token != null) {
            builder.header("Authorization", "Bearer " + token);
        }
        return chain.proceed(builder.build());
    }
}
