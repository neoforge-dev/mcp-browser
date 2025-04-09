# Active Context - MCP Browser (v0.4.0)

## Current Focus Areas

1.  **Resource Mgmt Robustness**: Ensure pool/context cleanup is bulletproof.
2.  **Test Coverage**: Improve integration and error scenario testing.
3.  **Security**: Rate limiting, network isolation improvements.
4.  **Verification Agent**: Static analysis, security checks.
5.  **Monitoring**: Setup and integration.
6.  **DevEx**: API Docs, CLI tool.

## Recent Changes

*   **Phase 1 Stabilization Complete**: Resolved test hangs by refactoring fixtures (`conftest.py`, `test_resource_management.py`), improving `BrowserPool` cleanup logic, and refining timeouts (`pyproject.toml`).
*   Core frontend analysis APIs completed.
*   MCP protocol extensions implemented.
*   WebSocket event subscriptions functional (with filtering).
*   Basic security (AppArmor, non-root) in place.
*   Core documentation structure established.

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

## Open Questions / Blockers

*   Optimal event broadcast optimization strategy?
*   Efficient rate limiting details (limits, burst handling)?
*   Best static analysis/security tools to integrate?
*   Monitoring setup details (key metrics, alerting)?

## Current Sprint Goals (Refined for Phase 2)

1.  Enhance resource management cleanup robustness.
2.  Add test coverage for network isolation and error handling.
3.  Implement basic API rate limiting.
4.  Select and integrate a static analysis tool.
5.  Set up basic system monitoring (NetData).

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