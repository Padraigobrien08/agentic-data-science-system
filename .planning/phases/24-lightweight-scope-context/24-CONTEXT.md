# Phase 24: Lightweight Scope Context - Context

**Gathered:** 2026-04-25  
**Status:** Completed

## Goal

Treat scope as lightweight chat context that is visible and editable without reopening workspace-style setup.

## Decisions

- Scope belongs in the header as quiet chat metadata.
- Editing scope should stay inline and explain that it affects future prompts.
- Chat copy should refer to `chat` and `scope`, not `workspace`.

## Scope

- Chat header scope presentation
- Inline scope editor copy
- Chat runtime/status wording

## Deferred

- Named scope presets
- More advanced scope narrowing explanations
