# Frontend Development Guidelines

> Best practices for frontend development in this project.

---

## Overview

This project renders independent A/B/C static sites with Python/Jinja and packaged
vanilla JavaScript/ECharts. Product authority remains in
`packets/2026-09-22-sol-delivery/`; these guides describe implementation practice,
not a second product specification. Latest user-selected Kangzhe Design 6.1
is used selectively under the
1007V1 function-first contract; historical screenshots/receipts are not rewritten.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Module organization and file layout | To fill |
| [Component Guidelines](./component-guidelines.md) | Shared asset owner, report adapters, motion and evidence | Documented R24-66 |
| [Hook Guidelines](./hook-guidelines.md) | Custom hooks, data fetching patterns | To fill |
| [State Management](./state-management.md) | Local state, global state, server state | To fill |
| [Quality Guidelines](./quality-guidelines.md) | Grouped tests, actual browser evidence, release boundaries | Documented R24-66 |
| [Type Safety](./type-safety.md) | Type patterns, validation | To fill |

---

## How to Fill These Guidelines

For each guideline file:

1. Document your project's **actual conventions** (not ideals)
2. Include **code examples** from your codebase
3. List **forbidden patterns** and why
4. Add **common mistakes** your team has made

The goal is to help AI assistants and new team members understand how YOUR project works.

---

**Language**: All documentation should be written in **English**.
