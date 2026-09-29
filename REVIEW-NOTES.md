# Content Hub code and sheet review (2026-09-29)

## Changes in this review bundle

- Removed the duplicate `publish_due_youtube.py` invocation from `create-videos.yml`. `youtube-scheduler.yml` is the single scheduled due-publication worker.
- Added GitHub Actions concurrency groups to serialize manual/scheduled runs of Create Videos and YouTube Scheduler.
- Added a preflight check for required Create Videos secrets.
- Added explicit OAuth refresh in the scheduled publisher, health check, and cleanup scripts.
- Fixed Drive cleanup's file-ID parser to accept a raw Drive file ID, which is what the Apps Script stores in CONTENT column I.
- Apps Script patch: removed duplicate `jsonResponse_`, kept OCR error messages out of SOURCE TEXT so OCR retries work, preserved the exact case of the required title suffix, validated title/description/hashtag output, preserved false/zero SETTINGS values, marked unsupported inbox files, made Drive video upload idempotent by reusing a same-named file, restricted new publication queue rows to YouTube, and changed the old GitHub trigger-creation helper so it removes the time trigger rather than creating a second scheduler.
- Proposed workbook: set Facebook, Instagram, and TikTok destinations inactive and marked their existing READY publication rows DISABLED. This is a separate proposed copy; the original workbook is untouched.

## Important remaining items before production

1. **Apply the Apps Script patch in the actual Apps Script project**, then run `createGitHubVideoTrigger()` once to remove any old 5-minute Apps Script trigger. Do not create that trigger again. GitHub Actions owns the scheduled workflow.
2. **Apps Script locking is not yet comprehensive.** `scanInbox`, `processOCR`, `processAI`, and `createPublicationQueue` still need a coordinated lock/idempotency pass to prevent overlapping trigger executions.
3. **Publication queue scheduling needs a full rewrite** to account for existing scheduled slots and the real per-calendar-day cap. The current function only limits items it creates in a single execution. It also uses the Apps Script project timezone, not the `PUBLISH_TIMEZONE` setting. Set the Apps Script project timezone to `Africa/Accra` as a stopgap; this does not implement the full queue rewrite.
4. **YouTube upload crash window remains:** if YouTube accepts an upload but the Sheets update fails before the video ID is persisted, a later run can upload a duplicate. The comment is still created before the `UPLOADED` row is committed in the current Python script. A robust recovery design should persist the YouTube ID immediately after upload, then create/update the comment independently.
5. **Gemini retry policy is reduced but not fully redesigned.** Apps Script still makes three Gemini calls per item and retries transient errors. If calls are slow, keep batch sizes low and monitor execution duration.
6. **Drive upload idempotency uses the filename.** Ensure generated MP4 names remain deterministic as `<CONTENT_ID>.mp4`; if multiple same-named files already exist, the current patch reuses the first match.
7. **Google Sheets export is a snapshot, not a live connection.** The proposed workbook is for review/import only. It does not update the live Google Sheet automatically.
8. **Run live smoke tests before re-enabling unattended automation:** test one inbox image end-to-end, one upload, one scheduled publish, one failure alert, and cleanup only against a test item. Do not test cleanup against valuable live content.

## Workbook observations

- Tabs present: CONTENT, ACCOUNTS, DESTINATIONS, PUBLICATIONS, SETTINGS.
- The current export has YouTube, Facebook, Instagram, and TikTok marked active.
- PUBLICATIONS contains READY rows for non-YouTube destinations even though the current publisher only handles `YT-01`; these would remain queued but unprocessed.
- The current export contains historical/test statuses and dates. Review them before treating this workbook as a clean production baseline.

## Validation performed

- Python files compile with `python -m compileall`.
- All four workflow YAML files parse successfully.
- Patched Apps Script passes Node JavaScript syntax checking.
- No live Google APIs, YouTube upload, Drive deletion, or Apps Script deployment was performed in this environment.
