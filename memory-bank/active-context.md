# Active Context - MCP Browser (v0.4.0)

## Current Focus Areas

1.  **Resource Mgmt**: Implement context/pool management & cleanup.
2.  **Security**: Implement rate limiting, granular AppArmor, network isolation.
3.  **Verification Agent**: Integrate static analysis, test automation, security checks.
4.  **Monitoring**: Integrate NetData, Loki+Grafana, cAdvisor.
5.  **DevEx**: API Docs (w/ examples), CLI tool, example scripts.

## Recent Changes

*   Core frontend analysis APIs completed.
*   MCP protocol extensions implemented.
*   WebSocket event subscriptions functional (with filtering).
*   Basic security (AppArmor, non-root) in place.
*   Core documentation structure established.

## Technical Debt / Must-Have Tasks (Summary)

*   **Resource Mgmt**: Context mgmt, cleanup, event perf.
*   **Security**: Rate limiting, AppArmor, network isolation.
*   **Verification**: Static analysis, test automation, security checks.
*   **Monitoring**: NetData, Loki+Grafana, cAdvisor integration.
*   **DevEx**: API docs, CLI tool, examples.

## Active Decisions / Strategy

*   **Resource Mgmt**: Use context pooling; optimize event broadcasting.
*   **Security**: Use FastAPI middleware for rate limits; Docker network isolation.
*   **Verification**: Use pytest; integrate tools like SonarQube.
*   **Monitoring**: Use NetData (system), Loki+Grafana (logs), cAdvisor (containers).
*   **DevEx**: Use FastAPI docs; Click/Typer for CLI.

## Open Questions / Blockers

*   Optimal context management strategy (pooling/cleanup)?
*   Efficient rate limiting details (limits, burst handling)?
*   Best static analysis/security tools to integrate?
*   Monitoring setup details (key metrics, alerting)?
*   *Blocker*: Need to implement Resource Mgmt (context/pooling) for stability.
*   *Blocker*: Need to implement Security (rate limiting, network isolation).
*   *Blocker*: Need to select and integrate Verification/Monitoring tools.

## Current Sprint Goals

1.  Implement browser context management.
2.  Add rate limiting & security enhancements.
3.  Integrate verification tools.
4.  Set up monitoring infrastructure.
5.  Enhance DevEx (docs, tools).

## Current Work Focus
- Stabilizing the `pytest` test suite to resolve hanging issues during cleanup.
- Refactoring inconsistent test fixture usage.

## Identified Problems
- **Test Hang:** The test suite currently hangs during the session teardown phase, specifically within the `browser_pool` fixture's `cleanup` method, after `tests/test_resource_management.py::test_browser_pool_limits` fails.
- **Fixture Misuse:** `test_browser_pool_limits` incorrectly creates its own `BrowserPool` instead of using the shared session-scoped fixture from `conftest.py`, leading to inconsistent testing and likely contributing to cleanup issues.
- **Cleanup Robustness:** The current cleanup logic in `BrowserPool` and `BrowserInstance` may not be resilient enough to handle resources left in an inconsistent state by failed tests.
- **Technical Debt:** Excessive debug logging and temporary timeouts were added, needing removal/refinement.

## Next Steps (Phase 1: Stabilization)
1.  **Refactor `test_browser_pool_limits`:** Modify the test to use the shared session-scoped `browser_pool` fixture and validate its `max_browsers` limit. Rename for clarity (e.g., `test_shared_pool_max_browser_limit`).
2.  **Enhance Fixture Cleanup:** Improve error handling within `BrowserPool.cleanup`, `BrowserPool.close_browser`, and `BrowserInstance.close` to gracefully handle potentially faulty browser/context states.
3.  **Refine Logging & Timeouts:** Reduce log verbosity (use DEBUG level) and remove temporary `asyncio.wait_for` timeouts.
4.  **Verify:** Confirm the hang is resolved and tests run to completion.

## Future Steps (Phase 2 & 3)
- Evaluate test isolation needs (function-scoped fixture vs. improved session fixture).
- Add missing test coverage for network routing, error handling, and resource monitoring.
- Update Memory Bank (`system-patterns.md`, `progress.md`) upon completion of Phase 1. 