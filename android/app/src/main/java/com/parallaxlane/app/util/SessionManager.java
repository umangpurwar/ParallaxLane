package com.parallaxlane.app.util;

import android.content.Context;
import android.content.SharedPreferences;

import com.parallaxlane.app.model.ApiModels;

// Stores the login tokens and user details in SharedPreferences so the user stays signed in after closing the app.
public class SessionManager {

    private static final String PREF_NAME = "parallaxlane_session";
    private final SharedPreferences prefs;

    // Opens the private preferences file of the app.
    public SessionManager(Context context) {
        prefs = context.getApplicationContext().getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE);
    }

    // Saves everything the login response returns.
    public synchronized void saveLogin(ApiModels.LoginResponse login) {
        prefs.edit()
                .putString("access", login.access)
                .putString("refresh", login.refresh)
                .putString("name", login.displayName)
                .putString("org_name", login.orgName)
                .apply();
    }

    // Replaces both tokens after the server gives new ones.
    public synchronized void saveTokens(String access, String refresh) {
        prefs.edit().putString("access", access).putString("refresh", refresh).apply();
    }

    // Returns the access token sent with every request, or null when signed out.
    public synchronized String getAccessToken() {
        return prefs.getString("access", null);
    }

    // Returns the refresh token used to get a new access token, or null when signed out.
    public synchronized String getRefreshToken() {
        return prefs.getString("refresh", null);
    }

    // Returns the name of the signed in user.
    public String getName() {
        return prefs.getString("name", "");
    }

    // Returns the college or organisation name, or null when the user has not joined one.
    public String getOrgName() {
        return prefs.getString("org_name", null);
    }

    // Saves a new organisation name after joining with a code.
    public void saveOrgName(String orgName) {
        prefs.edit().putString("org_name", orgName).apply();
    }

    // Tells whether a user is signed in.
    public boolean isLoggedIn() {
        return getRefreshToken() != null;
    }

    // Deletes all saved values when the user signs out.
    public synchronized void clear() {
        prefs.edit().clear().apply();
    }
}
