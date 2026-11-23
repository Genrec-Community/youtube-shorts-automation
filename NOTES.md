# NOTES

## 2026-11-23 - Manual Instagram recovery for topic n1

- Video: n1 "Why you can sleep eight hours and still wake up groggy (sleep cycles and sleep inertia)", style B7.
- Source run: 45111204981 (render + YouTube upload, public https://youtu.be/__PRr2fBXb0).
- Recovery run: 45117014989 (ig-post.yml dispatched with artifact_run_id only; no pipeline rerun, no YouTube re-upload).
- Instagram: media_id 18472091044142895, container_id 17913042303375375, permalink https://www.instagram.com/reel/DgEnT8iESbZ/ on @things._.explained (IG user id 17841471261243238). Verified live and public 2026-11-23 about 10:52 IST.
- Durable receipt: state/receipts.csv records yt_status=uploaded and ig_status=published for n1, so future runs and any backfill treat n1 as published on both platforms. The source run predates per-run receipt persistence; this row was added by hand and byte-verified against the contents API.
- Hashtags: the published caption carries 19 hashtags; the standing target is 20 (IG_MAX_TAGS=20 in scripts/upload_instagram.py). n1's metadata yielded 19 unique tags after filtering. The live caption is intentionally left unchanged.
- Token: the IG_ACCESS_TOKEN repo secret was replaced on 2026-11-23. scripts/upload_instagram.py derives the linked Facebook Page token from /me/accounts at runtime and verifies the IG username before publishing. The user token's data-access expiry was observed as about 3 months in the owner's Meta token debugger (the exact data_access_expires_at is unobtainable without the Meta app secret); a renewal check is scheduled for about day 80.
