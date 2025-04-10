# Active Context - MCP Browser (Optimized)

## Current Focus: Debugging `page.goto()` Timeout

*   **Status**: Blocked on resolving `page.goto()` hang in Docker test environment (`test_allowed_domain_access`, etc.). Affects Phase 2 (Robustness) progress.
*   **History**: Ruled out network isolation code, launch args, Playwright versions (1.50/1.51), Xvfb requirement, D-Bus issues, specific Docker network config. Hang occurred with default bridge network.
*   **Current Step**: Trying to fix Docker build/runtime errors related to dependency installation and Python imports (`RateLimitMiddleware`, `BaseHTTPMiddleware`) after latest `Dockerfile` changes.
*   **Next Step (if build/runtime fixed)**: Re-run `make test` to check if `page.goto()` hang is resolved with latest `Dockerfile` and default bridge network.
*   **Hypothesis (if hang persists)**: Docker Desktop for Mac virtualization interaction with Playwright/Chromium IPC or sandboxing.

## Phase 2 Goals (Robustness Enhancement - Blocked/Partial)

1.  **Resolve `page.goto()` timeout.** (BLOCKER)
2.  Refine resource pool cleanup logic.
3.  Add test coverage (network routing, error handling, resource limits).
4.  Implement API rate limiting (Code added, needs testing).
5.  Select & integrate static analysis tool.
6.  Set up basic system monitoring (NetData).

## Blocked / Pending High-Priority Tasks

*   Test network routing rules (Requires `page.goto` fix).
*   Test rate limiting (Requires container to run).
*   Resource mgmt performance optimization.
*   Security hardening (Granular AppArmor, etc.).
*   Verification Agent integration.
*   Monitoring integration.
*   DevEx (API Docs, CLI).

## Recent Changes (Summary)

*   Fixed multiple Docker build errors (`poetry` vs `pip`, `README.md` missing, Python version mismatch).
*   Attempted to fix runtime errors (`BaseHTTPMiddleware` import, `RateLimiter` event loop).
*   Simplified `docker-compose.yml` networking (removed custom networks).
*   Removed Xvfb from `docker/xvfb-init.sh` and `docker-compose.yml` (temporarily).
*   Increased pytest timeout to 300s.
*   Tried Playwright v1.50.0 (vs v1.51.1).
*   Cleaned up D-Bus PID handling in `docker/xvfb-init.sh`.
*   Refactored test fixtures and `BrowserPool` cleanup (Phase 1).

## Key Decisions / Reminders

*   Using `pip install .` and `pip install -r requirements-test.txt` in `Dockerfile`.
*   Test timeout: 300s.
*   Playwright version: `v1.50.0-noble` base image (currently).
*   Default bridge network used in `docker-compose.yml` (currently).

## Open Questions
*   Root cause of `page.goto()` timeout?
*   Optimal event broadcast optimization strategy?
*   Rate limit details (limits, scope)?
*   Static analysis tool choice?
*   Monitoring config details (metrics, alerts)?

## Current Focus Areas

1.  **Resource Mgmt Robustness**: Ensure pool/context cleanup is bulletproof.
2.  **Test Coverage**: Improve integration and error scenario testing.
3.  **Security**: Rate limiting, network isolation improvements.
4.  **Verification Agent**: Static analysis, security checks.
5.  **Monitoring**: Setup and integration.
6.  **DevEx**: API Docs, CLI tool.

## Technical Debt / Must-Have Tasks (Summary)

*   **Resource Mgmt**: Perf optimization (high-volume events).
*   **Test Coverage**: Integration, error cases, network routing.
*   **Security**: Rate limiting, granular AppArmor, network isolation hardening.
*   **Verification**: Static analysis, test automation, security checks.
*   **Monitoring**: NetData, Loki+Grafana, cAdvisor integration.
*   **DevEx**: API docs, CLI tool, examples.

## Active Decisions / Strategy

*   **Resource Mgmt**: Continue with context pooling; optimize event broadcasting.
*   **Security**: Use FastAPI middleware for rate limits; Docker network isolation.
*   **Verification**: Use pytest; integrate tools like SonarQube.
*   **Monitoring**: Use NetData (system), Loki+Grafana (logs), cAdvisor (containers).
*   **DevEx**: Use FastAPI docs; Click/Typer for CLI.

## Current Sprint Goals (Refined for Phase 2)
1.  **Evaluate Test Isolation:** Assess if the current session-scoped fixture is sufficient or if function-scoped fixtures are needed for certain tests to prevent state leakage.
2.  **Add Network Routing Tests:** Create tests specifically for validating `allowed_domains` and `blocked_domains` functionality.
3.  **Add Error Handling Tests:** Test how the system behaves under various error conditions (e.g., Playwright errors, pool errors).
4.  **Refine Resource Monitoring Tests:** Expand tests for resource limit enforcement (CPU, detailed memory).
5.  **Update `system-patterns.md`**: Document fixture strategy and cleanup patterns.

## Current Work Focus
- **Phase 2: Enhancing Robustness**
  - Evaluate test isolation needs (function-scoped vs. session-scoped fixture).
  - Add test coverage for network routing, error handling, and resource monitoring scenarios.
  - Improve cleanup logic further if edge cases are found.

## Identified Problems (Previously Resolved)
- Test Hang: Resolved.
- Fixture Misuse: Resolved.
- Cleanup Robustness: Improved, ongoing refinement in Phase 2.
- Technical Debt: Logging/timeouts refined.

## Next Steps (Phase 2: Enhancing Robustness)
1.  **Evaluate Test Isolation:** Assess if the current session-scoped fixture is sufficient or if function-scoped fixtures are needed for certain tests to prevent state leakage.
2.  **Add Network Routing Tests:** Create tests specifically for validating `allowed_domains` and `blocked_domains` functionality.
3.  **Add Error Handling Tests:** Test how the system behaves under various error conditions (e.g., Playwright errors, pool errors).
4.  **Refine Resource Monitoring Tests:** Expand tests for resource limit enforcement (CPU, detailed memory).
5.  **Update `system-patterns.md`**: Document fixture strategy and cleanup patterns.

## Future Steps (Phase 3 and Beyond)
- Implement high-priority features (Security, Verification, Monitoring, DevEx).
- Optimize performance for high-volume event handling.
- Expand integration and performance testing. 