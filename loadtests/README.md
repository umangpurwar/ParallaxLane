# ParallaxLane Load Testing

## Prerequisites

- Backend running at `http://127.0.0.1:8000`
- Redis enabled for production-like rate limiting (`USE_REDIS_CACHE=True`)
- Seed load-test users and an active exam before running

## Locust (70 concurrent users)

```bash
pip install locust
locust -f loadtests/locustfile.py --host=http://127.0.0.1:8000
```

Headless 5-minute run:

```bash
locust -f loadtests/locustfile.py --host=http://127.0.0.1:8000 \
  --users 70 --spawn-rate 10 --run-time 5m --headless
```

## k6

```bash
k6 run loadtests/load_test.js
```

With custom exam:

```bash
K6_BASE_URL=http://127.0.0.1:8000 K6_EXAM_ID=1 k6 run loadtests/load_test.js
```

## Success criteria (70 users)

| Metric | Target |
|---|---|
| Error rate | < 5% |
| p95 response time | < 2000 ms |
| Heartbeat endpoint | No 500 errors |
| Live monitor | < 3000 ms p95 |
| Exam start | No duplicate active attempts |
| Submission storm | No DB deadlocks |

## Scenarios covered

- **Candidate flow**: login → list exams → heartbeat
- **Invigilator flow**: login → live monitor → exam list
- **Submission storm**: k6 start + heartbeat under 70 VUs
