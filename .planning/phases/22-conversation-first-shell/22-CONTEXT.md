# Phase 22: Conversation-First Shell - Context

**Gathered:** 2026-04-25  
**Status:** Completed

## Goal

Remove visible workspace-first framing from the primary product surface and make chat the unmistakable entry point.

## Decisions

- Keep the backend `project` model, but demote `workspace` as a visible product noun.
- Make the left rail start with `New chat`, not navigation chrome.
- Treat the main chat route as the primary entry point for signed-in use.

## Scope

- Chat shell header and left rail
- New-chat affordance from the chat surface
- Projects index and primary entry labels
- Landing and top-level copy that still frames the product as a workspace shell

## Deferred

- Deeper history semantics beyond the current persisted project/run model
- Cross-project comparison or pinned conversations
