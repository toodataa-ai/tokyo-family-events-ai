# RELEASE PROCESS

This repository uses a staging / production / release-snapshot model so repeated staging work never replaces the public site before review, and rollback always targets a version that was actually public.

## Branch roles

- `main`: staging/development. All normal edits and repeated trial-and-error happen here.
- `production`: the exact source used for the public root site.
- `release/*`: immutable snapshots of versions that were successfully deployed to the public site.

A `release/*` branch is **not** created for ordinary staging commits.

The authoritative list of rollback targets is:

- `.github/production-releases.json`

Current baseline public snapshot:

- `release/2026-10-08-baseline`

## URLs

- Public production: `https://toodataa-ai.github.io/tokyo-family-events-ai/`
- Hidden staging preview: `https://toodataa-ai.github.io/tokyo-family-events-ai/staging/`

The staging copy is not linked from the production UI. During deployment its HTML receives `noindex,nofollow` and a staging-only visual marker injected by CI. The marker is not stored in production source files.

## Normal development

1. Make any number of changes on `main`.
2. CI validates `main`.
3. The Pages workflow publishes:
   - root from `production`
   - `/staging/` from `main`
4. Review `/staging/` on desktop/mobile.
5. Continue changing `main` as many times as needed.
6. Do not move `production` until explicit approval.

Thus staging may contain many commits that were never public. Those commits are not rollback targets.

## Release after approval

1. Confirm the approved staging commit and ensure staging CI is green.
2. Record the current public release from `.github/production-releases.json`; this remains the immediate rollback target.
3. Move `production` to the approved staging commit.
4. Update `.github/release-trigger.txt` on `main` to trigger the Pages deployment.
5. Wait for the deployment workflow to succeed and verify the public root.
6. **Only after successful public deployment**, create a new immutable `release/YYYY-MM-DD-rN` branch from the deployed `production` commit.
7. Append that release ID, commit SHA, deployment timestamp and workflow run ID to `.github/production-releases.json` and set it as `current_public_release`.

This ordering is important: a candidate that never successfully reached the public site must never be registered as a public release snapshot.

## Rollback

Rollback targets are restricted to entries in `.github/production-releases.json`.

1. Choose a known-good past public release from the registry.
2. Confirm that the selected `release/*` branch points to the registered commit SHA.
3. Move `production` back to that release commit using force-with-lease semantics.
4. Update `.github/release-trigger.txt` on `main` with `operation=rollback` and the selected release ID.
5. Wait for the Pages workflow to succeed.
6. Confirm the public root now matches the selected historical public release.
7. Keep `main` unchanged so the newer/broken version remains available under `/staging/` for diagnosis.

Do **not** roll back directly to an arbitrary `main` commit, even if that commit looked good in staging. If it was never published and registered as a public release, it is not a rollback target.

## Safety rules

- Never edit user-facing production files directly on `production`.
- Never delete, rewrite or move a `release/*` snapshot after it has been registered.
- Never register a staging-only commit as a public release.
- A release is registered only after the public deployment has succeeded.
- A rollback target must exist in `.github/production-releases.json`.
- If staging validation fails, do not promote it.
- The public event count and production data must come from `production`, not from an unapproved `main` commit.
- Repeated staging changes are expected and may be discarded without affecting release history.
