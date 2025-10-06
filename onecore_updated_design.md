# ONECORE Logging Architecture - Reference for Optimization

**Purpose:** This document describes the intended architecture of ONECORE to help optimize the current logging setup. This is NOT a design specification - it's context about how the system is structured.

---

## The Nervous System Architecture

ONECORE follows a "nervous system" model where components have clear roles:

### Component Roles

| Component | Role | Biological Analogy |
|-----------|------|-------------------|
| **Interface** | I/O handling (captures user input, displays output) | Mouth/ears |
| **ONECORE (Adapter/Router)** | Protocol translation & routing between layers | Nervous system |
| **Orchestrator** | Planning & reasoning (converts intent to execution plans) | Brain |
| **Memory** | Conversation state (maintains context across turns) | Short-term recall |
| **State** | Cross-session persistence (resume conversations later) | Long-term memory |
| **MCP Servers** | Tool execution (TickTick, Calendar, etc.) | Hands/feet |

### Current Process Topology

```
┌─────────────────────────────────────────┐
│         Interface Layer                 │
│  (Chainlit / Textual / CLI)             │
└─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│      ONECORE (Adapter/Router)           │
│  - Routes between interface & orchestrator│
│  - Manages port contracts               │
│  - Handles component lifecycle          │
└─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│      Orchestrator (behind port)         │
│  - LangGraphAdapter (current)           │
│  - Plans operations                     │
│  - Executes via tools                   │
└─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│         MCP Servers                     │
│  (TickTick, Calendar, etc.)             │
│  - Separate processes                   │
│  - JSON-RPC over HTTP                   │
└─────────────────────────────────────────┘
```

---

## Current Logging Concerns

### What Exists Now
- Launcher (`app.py`) loads environment and validates API keys
- Each adapter (CLI, Chainlit, etc.) initializes its own logger
- Components log at various points in the flow
- Uncertainty about optimal logging boundaries

### Open Questions
1. **Where should logging be initialized?** (launcher vs adapter vs core)
2. **What should each layer log?**
   - Interface: User I/O events?
   - ONECORE: Routing decisions?
   - Orchestrator: Planning steps?
   - MCP calls: Request/response?
3. **How to correlate logs across components?** (session_id, turn_id, request_id?)
4. **Different outputs per interface?**
   - Chainlit: Maybe suppress verbose logs (rich UI)
   - CLI: Maybe show detailed logs (dev/debug)
   - Production: Structured JSON logs

---

## Architecture Principles (Relevant to Logging)

### 1. Adapters Are Thin
- Interfaces are thin wrappers (translate I/O format only)
- Core logic lives in ONECORE and orchestrator
- Adapters should not duplicate business logic

### 2. Orchestrator Is Pluggable
- Behind `OrchestratorPort` interface
- Could be LangGraph, Haystack, AG2, etc.
- Logging should work regardless of which orchestrator is active

### 3. Session Management Is Adapter-Specific
- CLI: Single session (`session_id = "default"`)
- Textual TUI: Multi-tab sessions
- HTTP: Session from headers/cookies
- But ONECORE/orchestrator needs session_id for memory

### 4. MCP Servers Are External Processes
- Separate containers/processes
- Communication via JSON-RPC over HTTP
- Should we log MCP requests/responses? Where?

---

## What NOT To Do (Per Architecture)

❌ **Don't log business logic in adapters** - they're thin I/O translators  
❌ **Don't duplicate logs between layers** - each layer logs its own concern  
❌ **Don't assume single interface** - logging must work for CLI/Chainlit/HTTP  
❌ **Don't couple to specific orchestrator** - works with any OrchestratorPort implementation  

---

## Request for Claude Code

**Given this architecture:**

1. Review the current logging setup in the codebase
2. Identify where logging boundaries are unclear or duplicated
3. Suggest optimal logging strategy that:
   - Respects layer responsibilities (interface, ONECORE, orchestrator, MCP)
   - Works across multiple interfaces (CLI, Chainlit, future HTTP)
   - Supports debugging without noise
   - Allows correlation across components (session_id, turn_id, etc.)
4. Propose concrete changes to align logging with the nervous system model

**DO NOT design the logging structure from scratch. Review what exists and optimize it based on the architecture described above.**

---

## Context: Why This Matters

ONECORE is designed to be a **platform for building assistants**, not just one assistant. The logging strategy must:
- Work when swapping interfaces (Chainlit → CLI → HTTP)
- Work when swapping orchestrators (LangGraph → Haystack → AG2)
- Support debugging complex flows (user input → routing → planning → MCP call → response)
- Not break when components are plugged/unplugged

The nervous system metaphor matters: each part of the system should log what IT is doing, not what other parts are doing.

---

**End of context. Analyze current codebase and suggest optimizations.**
