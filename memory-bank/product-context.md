# Product Context - MCP Browser (Optimized)

## Problem & Solution
*   **Problem**: AI agents lack secure, efficient, high-fidelity browser automation.
*   **Solution**: MCP Browser provides this via a dedicated service.

## Target Users & Goals
*   **AI Agents (L3/MCP)**: Need seamless control, rich feedback (visuals, DOM), stable API.
*   **DevOps**: Need simple deployment (`docker-compose`), config, monitoring.

## Key Features for AI
*   Interact with web apps (navigate, click, type).
*   Capture visuals (screenshots).
*   Inspect structure (DOM, CSS).
*   Detect rendering/accessibility issues.
*   Verify responsive design.

## Business Value
*   Enhances AI testing capabilities.
*   Reduces infra costs (vs. full browsers).
*   Improves dev efficiency (faster bug detection/debug).
*   Provides secure test environment.

## Key Success Metrics
*   **Performance**: < 3s startup, < 300MB RAM/instance.
*   **Agent Success**: High visual issue detection rate (>95%).
*   **Security**: Zero escapes from sandbox. 