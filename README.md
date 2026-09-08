# ParallaxLane v2.0

## Web-Based Online Examination and Proctoring System

ParallaxLane is a full-stack web application for conducting online examinations with integrated monitoring, supervision, and result management.

The system provides a Django REST API backend for authentication, organisation management, examinations, attempts, answer saving, monitoring, event tracking, and administration. A Vue.js frontend is included as the web client.

The backend is designed around server-authoritative exam state, organisation-level isolation, secure authentication, and reliable attempt handling.

---

## Overview

ParallaxLane supports the complete examination lifecycle:

```text
User Registration / Login
          ↓
Organisation Selection
          ↓
Exam Access
          ↓
Start / Resume Attempt
          ↓
Answer Questions
          ↓
Progressive Answer Saving
          ↓
Monitoring and Violation Tracking
          ↓
Exam Submission
          ↓
Result Generation
          ↓
Administrative Review
````

The Django backend acts as the authoritative source for exam timing, attempt state, permissions, answers, violations, and results.

---

# System Architecture

```text
                    REST API
                       ↓
┌──────────────────────────────────────────────┐
│                  Clients                     │
│                                              │
│      Vue.js Web Client / Future Clients      │
└──────────────────────┬───────────────────────┘
                       ↓
┌──────────────────────────────────────────────┐
│             Django + DRF Backend             │
│                                              │
│ Authentication                               │
│ Organisation Management                      │
│ Examination Management                       │
│ Attempt Management                           │
│ Answer Saving                                │
│ Monitoring                                   │
│ Attempt Events                               │
│ Administration                               │
│ Results / Reports                            │
└──────────────────────┬───────────────────────┘
                       ↓
                  Database
```

The client communicates with the backend exclusively through REST APIs.

---

# Backend System

The backend is built using:

* Django
* Django REST Framework
* JWT authentication
* PostgreSQL / configured Django database
* SMTP/Brevo-compatible email provider
* Database-backed monitoring and attempt events

The backend is responsible for:

* User registration and authentication
* OTP verification
* Password reset
* Google authentication
* Organisation and membership management
* Role-based access control
* Exam creation and management
* Exam attempts
* Server-authoritative exam deadlines
* Progressive answer saving
* Automatic evaluation
* Violation tracking
* Risk scoring
* Attempt event recording
* Live monitoring
* Result generation
* CSV report export
* Master Admin controls

---

# Authentication

ParallaxLane uses JWT-based authentication.

## Registration Flow

```text
Register
   ↓
Pending / Unverified account
   ↓
OTP verification
   ↓
Active account
   ↓
JWT authentication
```

## Supported Authentication Features

* Email/password login
* JWT access tokens
* JWT refresh tokens
* Refresh token rotation
* Token blacklisting
* OTP-based registration verification
* OTP-based password recovery
* Google authentication
* Logout
* Inactive-account protection

OTP security includes:

* Hashed OTP storage
* Expiration
* Single-use verification
* Previous OTP invalidation
* Rate limiting / lockout protections

---

# Multi-Organisation Architecture

ParallaxLane supports users belonging to multiple organisations.

Organisation membership determines the user's effective role within that organisation.

Supported organisation roles include:

* Owner
* Admin
* Invigilator
* Candidate

The selected organisation is used as the current working context, while actual authorisation is based on persisted organisation membership.

Users can:

* View their organisations
* Switch organisations
* Join organisations
* Join using an invitation or join code
* Manage organisation members
* Control exam access

Organisation-level isolation is enforced by the backend.

---

# Examination System

The examination system supports:

* Exam creation
* Exam configuration
* Questions
* Multiple-choice questions
* True/False questions
* Short-answer questions
* File/image-based answers
* Exam start and end times
* Attempt tracking
* Automatic evaluation
* Exam submission
* Result retrieval

## Server-Authoritative Exam Timing

Exam timing is controlled by the backend.

Each attempt stores a persistent deadline.

The effective deadline is based on:

```text
min(
    server-side attempt start + exam duration,
    exam end time
)
```

The client cannot extend or modify the deadline.

When an attempt is resumed, its original deadline is preserved.

Expired attempts are terminated and expired submissions are rejected.

---

# Progressive Answer Saving

Answers can be saved during an active attempt through the API.

```text
POST /api/exams/answers/save/
```

Example:

```json
{
    "attempt_id": 1,
    "question_id": 2,
    "answer": 5
}
```

Progressive saving provides:

* Immediate answer persistence
* Idempotent create/update behaviour
* Protection against duplicate answers
* Attempt ownership checks
* Organisation checks
* Question validation
* Deadline validation

The final submission grades the persisted answers.

---

# Monitoring

The monitoring system provides lightweight server-side recording of supported client-side violations.

Supported violations include:

* Tab switch
* Window blur
* Copy/paste activity

Violation severity is determined by the server.

The system records:

* Violation type
* Server timestamp
* Attempt
* Relevant metadata
* Risk contribution

Risk and violation counts are handled atomically to prevent concurrent requests from producing inconsistent state.

---

# Heartbeat

Active attempts can send heartbeat requests to the backend.

Heartbeat validation checks:

* Attempt ownership
* Organisation membership
* Active attempt state
* Server-authoritative deadline

Heartbeat requests do not themselves create attempt events.

---

# Attempt Events

ParallaxLane includes a database-backed `AttemptEvent` foundation for exam analytics and audit evidence.

Supported V1 events include:

* `attempt_started`
* `answer_saved`
* `answer_changed`
* `exam_submitted`
* `exam_terminated`

Events are:

* Append-only
* Server-timestamped
* Associated with an attempt
* Indexed for efficient lookup
* Failure-isolated

The V1 implementation intentionally avoids fabricated events that the backend cannot reliably observe.

---

# Administrative System

Administrative APIs are organisation-scoped.

Administrators can manage and monitor:

* Exams
* Users
* Exam attempts
* Results
* Monitoring information
* Exam configuration
* Exam activation/deactivation
* Organisation members
* Exam access

Live monitoring includes persisted attempt state, violations, and risk information.

---

# Master Admin

ParallaxLane also provides a global Master Admin layer separate from organisation-level roles.

Master Admin functionality includes:

```text
GET  /api/master-admin/status/
GET  /api/master-admin/organisations/
GET  /api/master-admin/organisations/<id>/
GET  /api/master-admin/settings/organisation-creation/
PATCH /api/master-admin/settings/organisation-creation/
```

Master Admin access is restricted to superusers.

Organisation creation can be enabled or disabled through the Master Admin configuration.

The database-backed setting is authoritative over the environment default.

---

# Organisation API

Important organisation endpoints include:

```text
POST /api/organisations/create/
GET  /api/organisations/my/
POST /api/organisations/<slug>/switch/
POST /api/organisations/join/
POST /api/organisations/join-by-code/
GET  /api/organisations/settings/
POST /api/organisations/<slug>/invite/
GET  /api/organisations/<slug>/members/
POST /api/organisations/<slug>/members/<id>/toggle-exam-access/
GET/POST /api/organisations/<slug>/join-code/
```

Invitation handling includes concurrency-safe capacity checks.

---

# Examination API

Important examination endpoints include:

```text
GET  /api/exams/
GET  /api/exams/<id>/
POST /api/exams/start/
POST /api/exams/answers/save/
POST /api/exams/submit/
GET  /api/exams/my-results/
```

The backend prevents unsafe question replacement when an active attempt already contains saved answers.

Exam deletion is also protected when attempt history exists.

---

# Monitoring API

```text
POST /api/monitoring/log/
POST /api/monitoring/heartbeat/
```

The backend validates the attempt, organisation, active state, and deadline before accepting monitoring requests.

---

# Reporting

Administrative exam reports are exported as CSV.

```text
GET /api/admin/exam/<exam_id>/export/
```

Reports can contain:

* Candidate information
* Exam information
* Organisation information
* Attempt timing
* Status
* Score
* Risk information
* Answers
* Selected options
* Violations
* Violation metadata
* Attempt events
* Event metadata

CSV output is escaped correctly and remains valid even when no result data exists.

---

# Security and Reliability

The backend includes protections for:

* Organisation-level isolation
* Role-based authorisation
* Inactive-account login
* Password reset security
* OTP reuse
* OTP expiration
* Invitation race conditions
* Organisation capacity limits
* Concurrent violation updates
* Exam deadline enforcement
* Unsafe exam/question modifications
* Invalid attempt ownership
* Expired exam attempts
* Duplicate answer creation
* Concurrent attempt creation

State-changing operations use transactional logic where required to maintain consistency.

---

# Frontend

The current web client is built using:

* Vue.js
* Vue Router
* Axios
* Composition API

The frontend communicates with the Django REST API.

The backend itself remains independently usable by other API clients.

---

# Tech Stack

## Backend

* Python
* Django
* Django REST Framework
* JWT
* Database-backed event and monitoring system

## Frontend

* Vue.js
* Vue Router
* Axios

## Development

* Git
* Python virtual environment
* Node.js / npm

---

# Project Structure

```text
parallaxlane/
│
├── backend/
│   ├── accounts/
│   ├── admin_panel/
│   ├── attempt_events/
│   ├── core/
│   ├── exams/
│   ├── monitoring/
│   ├── organisations/
│   ├── docs/
│   ├── manage.py
│   ├── requirements.txt
│   └── ...
│
├── frontend/
│   ├── src/
│   ├── components/
│   ├── views/
│   ├── router/
│   └── ...
│
└── README.md
```

---

# Backend Setup

```bash
cd backend

python -m venv venv
```

Windows:

```powershell
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run migrations:

```bash
python manage.py migrate
```

Run the backend:

```bash
python manage.py runserver
```

The API is then available at:

```text
http://127.0.0.1:8000/
```

---

# Local Network Development

For testing an Android client or another device on the same local network, Django can be started on all network interfaces:

```bash
python manage.py runserver 0.0.0.0:8000
```

The client can then communicate with the laptop using its local network address:

```text
http://<LAPTOP-IP>:8000/
```

The required Django host configuration must allow the corresponding development address.

---

# API Health Check

The backend provides:

```text
GET /api/health/
```

This can be used to verify that the API is reachable before testing authenticated functionality.

---

# Testing

The backend includes an automated Django test suite covering authentication, organisations, examinations, monitoring, concurrency, security, administration, reporting, and related functionality.

The final V1 backend verification currently passes:

```text
144 tests
144 passed
0 failed
```

Standard verification commands:

```bash
python manage.py check
python manage.py makemigrations --check
python manage.py test --keepdb
```

---

# Current V1 Scope

The current V1 backend focuses on:

* Secure authentication
* Multi-organisation support
* Organisation roles and access control
* Server-authoritative exam timing
* Exam attempts
* Progressive answer saving
* Automatic evaluation
* Monitoring violations
* Risk tracking
* Database-backed attempt events
* Administrative monitoring
* CSV reporting
* Master Admin controls

---

# Current Limitations

The system still has limitations inherent to browser/client-side monitoring.

Examples include:

* Client-side monitoring can potentially be bypassed
* Monitoring signals are limited to events observable by the client
* No AI-based behavioural detection
* No fully real-time WebSocket monitoring in V1
* No server-side camera analysis in V1

---

# Future Scope

Potential future improvements include:

* Android/mobile clients
* WebSocket-based real-time monitoring
* Advanced analytics
* AI-assisted proctoring
* Advanced behavioural detection
* Expanded audit/event analytics
* Additional monitoring signals
* Production cloud deployment

---

# Version

**ParallaxLane v1.3.2**

Backend status:

**V1 backend frozen and verified.**

---

# Author

**UMNG**

