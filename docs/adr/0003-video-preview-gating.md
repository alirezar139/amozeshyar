# ADR 0003: Physically-truncated preview clip instead of a client-side watch-time limit

## Status
Accepted

## Context
The product requires: anyone can watch a free preview of a lesson video (default 30 seconds, configurable via `videos.PreviewPolicy` and per-course override), then must purchase the course to keep watching. The naive implementation — serve the full video file and stop playback client-side after N seconds via JavaScript — is trivially bypassed (devtools, disabling JS, or hitting the underlying file URL directly), which would undermine the entire commercial model.

## Decision
On upload, a Celery task (`apps.videos.services.transcoder`) uses ffmpeg to produce two *separate* artifacts:
1. `hls_master_key` — the full transcoded HLS rendition, stored privately, reachable only via a signed URL issued by `ManifestView`, which re-checks `Enrollment` on every call.
2. `preview_clip_key` — a physically truncated clip containing no more than the configured preview length, stored privately, reachable via a signed URL issued by `PreviewStreamView` (no auth/enrollment check needed, because the object itself cannot expose more than the free portion).

Non-enrolled viewers are only ever handed a signed URL to the preview object. There is no scenario where the bytes of the full lesson are reachable by an anonymous or non-enrolled request — the gate is enforced by what exists on disk, not by trusting the client to stop.

`WatchSession` records are still created on every preview/manifest fetch, primarily for audit/analytics and as a hook for future concurrent-session limits — they are not the security boundary.

## Consequences
- Doubles storage for the preview-eligible portion of each video (negligible — previews are short) and adds one extra ffmpeg pass per upload.
- Changing a course's preview length after upload requires re-running the transcode task for existing lessons (not automatic) — acceptable for MVP since this changes rarely.
- Signed URLs (`AWS_QUERYSTRING_EXPIRE`, 10 min) still expire quickly as defense-in-depth, so even a leaked manifest link stops working shortly after.
