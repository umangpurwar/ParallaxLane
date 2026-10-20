# ParallaxLane Android App: System Design

A mini project for the Mobile Application Development course. The app lets a student sign in, take an online exam on their phone and see their score. The Django backend (ParallaxLane) holds all the data, checks answers and decides when an exam ends. The app shows data and sends what the student does.

## 1. Overall architecture

```
+----------------------------+          HTTPS / JSON          +-----------------------------+
|        Android app         |  <-------------------------->  |   Django REST backend       |
|                            |                                |                             |
|  Activities (screens)      |   login, exams, answers,       |  Accounts, devices          |
|  Retrofit + OkHttp + Gson  |   heartbeat, violations        |  Organisations              |
|  SharedPreferences         |                                |  Exams, attempts, grading   |
|  Android Keystore          |                                |  Monitoring, violations     |
+----------------------------+                                +-----------------------------+
                                                                         |
                                                                PostgreSQL + Redis
```

The app is a client only. It never knows the correct answers and never calculates a score.

## 2. Layers inside the app

| Layer | Package | Classes | Job |
|---|---|---|---|
| Screens | `ui` | LoginActivity, DeviceActivity, ExamListActivity, ExamAdapter, ExamActivity, ResultActivity, ResultsActivity | Show data, take input, call the API |
| Network | `api` | ApiService, ApiClient, HeaderInterceptor, TokenAuthenticator, ApiError | Send requests and read responses |
| Data | `model` | ApiModels | Java classes that match the JSON of each request and response |
| Helpers | `util` | SessionManager, DeviceHelper, AppUtils | Save login, identify the phone, small shared functions |

Each screen is one Activity. Screens move with Intents and pass small values (exam id, attempt id, time left) as Intent extras.

## 3. Screen flow

```
LoginActivity --(login ok)--> DeviceActivity --(phone approved)--> ExamListActivity
                                   |                                   |   |   |
                          (pending: Check again)          (tap exam)   |   |   +--> menu: Join with code (dialog)
                                                                       |   +------> menu: Results --> ResultsActivity
                                                                       v
                                                                 ExamActivity --(submit)--> ResultActivity
                                                                       |
                                                          (ended by server) --> ResultsActivity
```

If the student is already signed in, LoginActivity skips straight to DeviceActivity. If the phone is already approved, DeviceActivity opens the exam list at once.

## 4. What each screen sends and receives

| Screen | Request | Backend endpoint | What the app does with the response |
|---|---|---|---|
| Login | email, password | `POST login/` | Saves tokens, name and college name in SharedPreferences |
| Device | phone id, public key, model | `POST accounts/devices/register/` | Approved: open exams. Pending: show waiting message |
| Device | none | `GET accounts/devices/me/` | Same as above, used by Check again |
| Exam list | none | `GET exams/` | Fills the RecyclerView |
| Exam list | code | `POST organisations/join-by-code/` | Saves the college name, reloads exams |
| Exam list | none | `POST exams/<id>/challenge/` | Gets a one time text to sign |
| Exam list | signed text | `POST exams/<id>/start/` | Gets attempt id and deadline, opens the exam |
| Exam | none | `GET exams/<id>/` | Gets the questions (only given during your own attempt) |
| Exam | attempt, question, answer | `POST exams/answers/save/` | Shows Saved or Not saved |
| Exam | phone state | `POST monitoring/heartbeat/` every 10 s | Ends the exam if the server says it is over |
| Exam | violation type | `POST monitoring/log/` | Shows a warning, or ends the exam if the server terminated it |
| Exam | all answers | `POST exams/<id>/submit/` | Opens the result screen with the score |
| Results | none | `GET exams/my-results/` | Shows one line per finished exam |
| Any | refresh token | `POST token/refresh/` | Done automatically by TokenAuthenticator when a token expires |

## 5. Open source libraries and why they are used

All libraries are added in `app/build.gradle` and downloaded by Gradle. None of their source code is copied or changed. Everything inside `com.parallaxlane.app` is code written for this project.

| Library | Repository | What it provides | Why it is used here |
|---|---|---|---|
| AndroidX AppCompat | github.com/androidx/androidx | Activity base class, action bar, AlertDialog | Standard base for every screen |
| Material Components | github.com/material-components/material-components-android | Button, outlined button, theme | Black and white buttons without custom drawing |
| AndroidX RecyclerView | github.com/androidx/androidx | Scrollable list with view recycling | Exam list |
| AndroidX SwipeRefreshLayout | github.com/androidx/androidx | Pull down to refresh | Reloading the exam list |
| Retrofit 2 | github.com/square/retrofit | Turns a Java interface into HTTP calls | Every backend call is one method in ApiService |
| OkHttp + logging interceptor | github.com/square/okhttp | HTTP client, interceptors, authenticator | Adding headers, refreshing tokens, logging in debug |
| Gson (via Retrofit converter) | github.com/google/gson | JSON to Java objects and back | Reading backend responses into ApiModels |
| Glide | github.com/bumptech/glide | Loads and caches images from a URL | Question images |

Android platform APIs used directly (part of Android itself, not libraries): SharedPreferences, Android Keystore, CountDownTimer, Handler, ActivityManager (screen pinning), WindowManager (FLAG_SECURE).

## 6. What the custom code does

- **ApiService:** lists the backend endpoints for Retrofit. No logic.
- **ApiClient:** builds Retrofit and OkHttp once with the server address and returns the same instance to every screen.
- **HeaderInterceptor:** adds four headers to every request: client type, app version, phone id and login token.
- **TokenAuthenticator:** when the server says the token expired (401), gets a new one once and repeats the request.
- **ApiError:** reads the `code` and `error` fields the backend sends on failure.
- **SessionManager:** saves and reads the tokens with SharedPreferences.
- **DeviceHelper:** hashes the Android ID and creates a signing key in the Android Keystore.
- **Activities:** connect buttons and lists to API calls and show the results.

## 7. How the exam is protected (course level)

| Risk | What the app does | Android feature used |
|---|---|---|
| Screenshots or screen recording of questions | Exam screen is marked secure, captures come out black | `FLAG_SECURE` |
| Switching to another app | Screen is pinned with `startLockTask()`, leaving is reported | Screen pinning, `onStop` |
| Split screen | Reported as a violation | `onMultiWindowModeChanged` |
| Unpinning the screen | Checked every 10 seconds, reported | `ActivityManager.getLockTaskModeState` |
| Taking the exam from a laptop | Exam start must be signed by a key that exists only on the approved phone | Android Keystore |
| Closing the app or turning on airplane mode | Heartbeats stop and the server records the gap on its own | Handler, server side check |
| Changing the phone clock | Timer counts down from the time the server gave, not the phone clock | CountDownTimer |
| Pressing back | Back button is blocked during the exam | OnBackPressedCallback |

The server decides everything: when a warning is serious, when the exam is over and what the score is. The app only reports.

## 8. Avoiding leaks and crashes

- Every Retrofit callback checks `isDestroyed()` before touching views, so a late response never updates a closed screen.
- The exam timer and the heartbeat Handler are stopped in `onDestroy`, so nothing keeps running after the screen closes.
- Retrofit and OkHttp are created once, using the application context rather than an Activity, so no screen is held in memory by them.
- Token refresh is a `synchronized` method, so two requests can never refresh at the same time.
- The exam screen is locked to portrait and handles theme changes itself, so it is never recreated in the middle of an exam.

## 9. Known limits (to mention in the viva)

- **Token storage:** tokens are kept in private SharedPreferences, not encrypted. A rooted phone could read them. This is fine for a mini project; a production app would encrypt them.
- **Unsaved answers:** an answer that failed to save is kept only in memory and is sent again with the final submit. If the app is killed before submit, that answer is lost. Answers that were saved are safe on the server.
- **Screen off counts as leaving:** turning the screen off during an exam counts as leaving the app, because Android calls `onStop`.
- **Not prevented:** a second phone, another person, or a photo of the screen taken with another camera.
- **Play Integrity:** checks for rooted or modified phones are left out. The backend keeps `INTEGRITY_REQUIRED=False` for this project.
- **Single college per session:** switching between several colleges is left out; the app uses the college returned at login, or the one joined with a code.

## 10. Running the project

1. **Create the project in Android Studio:**
   - Template: Empty Views Activity
   - Name: ParallaxLane
   - Package: `com.parallaxlane.app`
   - Language: Java
   - Minimum SDK: API 26
   - Build configuration language: Groovy DSL
2. **Copy the files:** close Android Studio and copy the contents of this folder over the project, replacing files. Keep the generated `gradle/wrapper`, `gradlew`, `gradlew.bat` and the `mipmap` icon folders. Delete the generated `MainActivity.java`.
3. **Set the server address** in `gradle.properties`:
   - Emulator: keep `SERVER_URL=http://10.0.2.2:8000/api/`.
   - Real phone on the same Wi-Fi: use your PC's address, for example `http://192.168.1.5:8000/api/`.
4. **Start the backend** with `python manage.py runserver 0.0.0.0:8000`, and add your PC's address to `ALLOWED_HOSTS`.
5. **Enable pinning on the phone:** Settings, Security, App pinning.
6. **Build:** run `.\gradlew.bat assembleDebug`, or press Run in Android Studio.

## 11. Verification status

- **Not built yet.** The project has not been compiled; the environment used to write it cannot download Android libraries from Google's servers.
- **Checked:** every Java file was parsed for syntax and every XML file checked as valid XML, and the request and response fields match the backend contract `ANDROID_API_CONTRACT_v1.md`.
- **First real test:** the first build in Android Studio. Report any error there as it appears.
- **Target SDK 34:** chosen on purpose. Android 15 forces edge to edge layouts on apps that target 35, which would put the action bar under the status bar. This is fine for a college project. A Play Store release would need target 35 or higher and inset handling.
