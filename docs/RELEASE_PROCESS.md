# RELEASE PROCESS

This repository uses a two-track release model so development work never replaces the public site before review.

## Branch roles

- `main`: staging/development. All normal edits go here first.
- `production`: the exact source used for the public root site.
- `release/*`: immutable release snapshots used for rollback.

Current baseline snapshot:

- `release/2026-10-08-baseline`

## URLs

- Public production: `https://toodataa-ai.github.io/tokyo-family-events-ai/`
- Hidden staging preview: `https://toodataa-ai.github.io/tokyo-family-events-ai/staging/`

The staging copy is not linked from the production UI. During deployment its HTML receives `noindex,nofollow`.

## Normal development

1. Make changes only on `main`.
2. CI validates `main`.
3. The Pages workflow publishes:
   - root from `production`
   - `/staging/` from `main`
4. Review `/staging/` on desktop/mobile.
5. Do not move `production` until approval.

Thus a staging push can update the hidden preview while the public root continues to use the unchanged `production` branch.

## Release after approval

1. Confirm staging CI is green.
2. Record the current `production` commit if needed.
3. Move/merge `production` to the approved `main` commit.
4. Create a new snapshot branch such as `release/YYYY-MM-DD-rN` from the released production commit.
5. Update `.github/release-trigger.txt` on `main`.
6. The main Pages workflow redeploys, taking the public root from the new `production` commit.
7. Confirm the public root and production CI behavior.

No user-facing release occurs merely because `main` changed.

## Rollback

1. Choose a known-good `release/*` snapshot.
2. Move `production` back to that snapshot commit using force-with-lease semantics.
3. Update `.github/release-trigger.txt` on `main` with `operation=rollback` and the selected snapshot.
4. The main Pages workflow redeploys the public root from the restored `production` commit.
5. Keep `main` unchanged so the broken/newer version remains available under `/staging/` for diagnosis.

Rollback changes only the public source pointer; release snapshots are never edited after creation.

## Safety rules

- Never edit user-facing production files directly on `production`.
- Never delete or rewrite a `release/*` snapshot.
- A release/rollback is complete only after the Pages workflow succeeds.
- If staging validation fails, do not promote it.
- The public event count and production data must come from `production`, not from an unapproved `main` commit.
