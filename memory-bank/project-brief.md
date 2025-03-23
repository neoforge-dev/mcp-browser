# MCP Browser - Project Brief

## Overview
MCP Browser is an enterprise-grade browser automation solution designed to work as a smart browser for L3 coding agents. It enables AI agents to test frontend applications in real browser environments, evaluate outputs, and identify frontend-related issues.

## Core Requirements

1. **Browser Automation Platform**
   - Headless browser execution with Playwright
   - Real browser rendering metrics and analysis
   - Virtual display server (Xvfb) for headless operation

2. **Security by Default**
   - AppArmor profiles for container security
   - Non-root execution of browser processes
   - Environment-based credential management
   - Resource limiting to prevent exhaustion
   - Isolated display server with Xvfb

3. **Deployment & Operations**
   - One-command deployment (similar to Nomad)
   - Docker containerization for consistent environments
   - Resource pooling and cost controls
   - Monitoring and metrics collection

4. **Verification & Testing**
   - Static code analysis (Bandit/Semgrep)
   - Automated testing pipeline
   - Security validation checks
   - Frontend rendering verification

5. **Agent Integration**
   - MCP (Model Control Protocol) interface for AI agents
   - Websocket communication for real-time updates
   - API for programmatic browser control
   - Screenshot and DOM analysis capabilities

## Technical Architecture

```
graph TD
    A[Claude Desktop] --> B[SSH Tunnel]
    B --> C[Older Mac/Linux PC]
    C --> D[Playwright in Docker]
    D --> E[Headless Chromium]
    D --> F[Resource Monitor]
    C --> G[MCP Server]
    G --> H[Security Sandbox]
```

## Success Criteria

1. Deploy browser automation with a single command
2. Run browser tests in isolated, secure containers
3. Provide accurate rendering analysis
4. Operate efficiently on modest hardware (90% less RAM than full browsers)
5. Maintain comprehensive security controls
6. Enable AI agents to effectively identify frontend issues

## Out of Scope

1. Full browser UI for human interaction
2. Plugin or extension management
3. Multi-user session management
4. Complex browser fingerprinting or anti-detection features 