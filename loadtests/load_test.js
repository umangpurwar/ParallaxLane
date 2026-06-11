/**
 * ParallaxLane k6 load test — 70 VUs, exam traffic simulation.
 *
 * Install: https://k6.io/docs/get-started/installation/
 * Run:     k6 run loadtests/load_test.js
 *
 * Env:
 *   K6_BASE_URL=http://127.0.0.1:8000
 *   K6_EXAM_ID=1
 */

import http from "k6/http";
import { check, sleep } from "k6";

const BASE = __ENV.K6_BASE_URL || "http://127.0.0.1:8000";
const EXAM_ID = __ENV.K6_EXAM_ID || "1";

export const options = {
  stages: [
    { duration: "1m", target: 35 },
    { duration: "2m", target: 70 },
    { duration: "2m", target: 70 },
    { duration: "1m", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(95)<2000"],
  },
};

function login(email) {
  const res = http.post(
    `${BASE}/api/login/`,
    JSON.stringify({ email, password: "TestPass1!" }),
    { headers: { "Content-Type": "application/json" } }
  );
  check(res, { "login ok": (r) => r.status === 200 });
  return res.json("access");
}

export default function () {
  const vu = __VU;
  const token = login(`candidate${(vu % 70) + 1}@loadtest.com`);
  if (!token) return;

  const headers = {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };

  http.get(`${BASE}/api/health/`);
  http.get(`${BASE}/api/exams/`, { headers });

  const startRes = http.post(`${BASE}/api/exams/${EXAM_ID}/start/`, null, { headers });
  if (startRes.status === 200) {
    const attemptId = startRes.json("attempt_id");
    http.post(
      `${BASE}/api/monitoring/heartbeat/`,
      JSON.stringify({ attempt_id: attemptId }),
      { headers }
    );
  }

  sleep(Math.random() * 3 + 1);
}
