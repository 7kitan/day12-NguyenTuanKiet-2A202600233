> [!IMPORTANT]
> **Scorers/Instructors:** Please refer to the **[INSTRUCTOR_GUIDE.md](./INSTRUCTOR_GUIDE.md)** for detailed assessment criteria and grading rubric.

# Day 12 — Cloud Infrastructure & Deployment: Submission

**Student:** Nguyễn Tuấn Kiệt  
**ID:** 2A202600233  
**Project:** AICB-P1 · VinUniversity 2026

This repository contains the completed lab exercises and final project for Day 12 (Deployment).

---

## 📂 Submission Overview

The core of the submission is contained in the following files and directories:

| Deliverable | Location | Description |
|-------------|----------|-------------|
| **Main Answer Sheet** | [MISSION_ANSWERS.md](./MISSION_ANSWERS.md) | Contains all theoretical answers and technical proof for Parts 1-6. |
| **Final Project (Part 6)**| [my-production-agent/](./my-production-agent/) | The complete production-ready agent built from scratch. |
| **Scaling Refactor** | [05-scaling-reliability/](./05-scaling-reliability/production/) | Implementation of the stateless design and load balancing. |
| **Screenshots** | [screenshots/](./screenshots/) | Visual proof of deployment and monitoring states. |

---

## 🚀 Final Project (Part 6)

The final project is a production-grade AI agent deployed on Railway.

- **Public URL**: [https://my-production-agent-lab12-production.up.railway.app/](https://my-production-agent-lab12-production.up.railway.app/)
- **Features**:
  - Stateless conversation history (Redis List).
  - Defense-in-depth: API Key Auth, Rate Limiting, Cost Guard.
  - Reliability: Health/Ready probes, Graceful Shutdown.
  - Infrastructure: Optimized Multi-stage Docker build.

---

## 🛠️ How to Verify

### 1. Verification of Scaling & Reliability (Part 5)

To verify the stateless design and load balancing, ensure the Docker stack is running (in `05-scaling-reliability/production`) and execute:

```bash
python3 05-scaling-reliability/production/test_stateless.py
```

*Expected: Requests will be served by different instances while maintaining session history via Redis.*

### 2. Verification of Final Project (Part 6)

To verify that the final project meets all production-readiness criteria:

```bash
cd my-production-agent
python3 check_production_ready.py
```

*Expected: 20/20 checks passed (100% score).*

### 3. Verification of Health & Security

You can test the live endpoints of the final project:

- **Health Check**: `curl https://my-production-agent-lab12-production.up.railway.app/health`
- **Readiness Check**: `curl https://my-production-agent-lab12-production.up.railway.app/ready`

---
