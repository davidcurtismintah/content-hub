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
2. Added a shared Apps Script lock around `scanInbox`, `processOCR`, `processAI`, and `createPublicationQueue`. The lock prevents these trigger handlers from mutating the shared queue concurrently; each wrapper skips quickly if another handler owns the lock. A stale `AI_PROCESSING` row is eligible for retry on the next run.
3. Rewrote publication scheduling to use `PUBLISH_TIMEZONE`, skip occupied date/time slots, and enforce `PUBLISH_MAX_POSTS_PER_DAY` against existing scheduled content per calendar day. It appends rows in one batch. Review existing historic rows before relying on its daily counts.
4. YouTube publisher commits `UPLOADED` + video ID before attempting the standard comment, and retries a missing comment without re-uploading. New uploads carry a stable `contenthub_<CONTENT_ID>` YouTube tag. Before uploading a `READY` row, the publisher scans up to 150 recent channel uploads for that tag and restores the video ID to Sheets if it finds a match. This substantially closes the lost-Sheets-write crash window. It cannot recover an untagged legacy upload, or one that has fallen outside the 150 most recent uploads; those require manual reconciliation. The check also fails closed: if it cannot inspect the channel, it will not risk uploading a duplicate.
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
- Patched Apps Script passes Node JavaScript syntax checking (checked as a `.js` source file).
- No live Google APIs, YouTube upload, Drive deletion, or Apps Script deployment was performed in this environment.
- Added YouTube upload reconciliation by stable per-content tag; Python syntax was rechecked after the change.

## Apply carefully

- Replace the Apps Script project code with `apps-script/Content-Hub-Connector.gs` (or use the separately supplied `.gs` file), save, then inspect triggers. Keep only one trigger each for `scanInbox`, `processOCR`, `processAI`, and `createPublicationQueue`; do not create a timer trigger for `triggerGitHubVideoWorkflow`.
- Verify `PUBLISH_TIMEZONE` is `Africa/Accra`. The queue code now reads that setting.
- Do not import the proposed workbook over the live spreadsheet without reviewing historical rows. The proposed workbook is a review copy, not a live sync.
- Before production, test the queue on a duplicate/test spreadsheet with dates and times covering: occupied slots, a full daily cap, a past start time, and a slot crossing midnight.
