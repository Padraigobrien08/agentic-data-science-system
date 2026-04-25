# Phase 23: Chat History and Continuity - Context

**Gathered:** 2026-04-25  
**Status:** Completed

## Goal

Make history feel like conversation continuity rather than a list of generic analyses or run links.

## Decisions

- History remains project-backed, but it should point back into chat first.
- History labels should prefer the answer thesis over raw run metadata.
- Reopening prior work should keep the user in the chat transcript whenever possible.

## Scope

- Chat history builder
- Left rail history labels and previews
- In-chat return behavior for prior answers

## Deferred

- Cross-chat history in the left rail
- Pinned conversations and saved answer collections
