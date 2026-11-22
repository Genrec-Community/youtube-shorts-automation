#!/usr/bin/env python3
"""Publish a Reel to Instagram via the Graph API (Facebook Login user token, Page-linked account).

Needs env IG_ACCESS_TOKEN (Facebook user token with instagram_basic,
instagram_content_publish, pages_show_list, pages_read_engagement).
Optional env IG_USER_ID (expected Instagram account id) and IG_EXPECTED_USERNAME
(default things._.explained). The target account is resolved from /me/accounts and
must match the expected username (and IG_USER_ID when set), otherwise nothing is
published. Meta fetches the video from --video-url, which must be public.

Usage: upload_instagram.py --video-url URL --metadata metadata.json
Writes instagram_result.json next to the metadata file. Never prints the token.
"""
import argparse, json, os, sys, time, urllib.parse, urllib.request, urllib.error

API = "https://graph.facebook.com/v23.0"
TOK = os.environ.get("IG_ACCESS_TOKEN", "")


def call(method, path, data=None):
    url = API + path
    body = None
    if method == "GET":
        url += ("&" if "?" in url else "?") + "access_token=" + urllib.parse.quote(TOK)
    else:
        d = dict(data or {})
        d["access_token"] = TOK
        body = urllib.parse.urlencode(d).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=body, method=method), timeout=60) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode()).get("error", {})
        except Exception:
            err = {}
        return e.code, {"error": {"type": err.get("type"), "code": err.get("code"),
                                   "subcode": err.get("error_subcode"),
                                   "message": str(err.get("message", ""))[:300]}}
    except Exception as e:
        return -1, {"error": {"type": type(e).__name__, "message": str(e)[:200].replace(TOK, "***") if TOK else str(e)[:200]}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video-url", required=True)
    ap.add_argument("--metadata", required=True)
    ap.add_argument("--caption", default="")
    a = ap.parse_args()
    expected_user = os.environ.get("IG_EXPECTED_USERNAME", "things._.explained")
    expected_id = os.environ.get("IG_USER_ID", "").strip()
    out_path = os.path.join(os.path.dirname(os.path.abspath(a.metadata)), "instagram_result.json")

    def done(status, **extra):
        json.dump({"status": status, **extra}, open(out_path, "w"))
        print("instagram:", status, json.dumps(extra)[:600])
        sys.exit(0 if status == "published" else 1)

    if not TOK:
        done("skipped", reason="missing IG_ACCESS_TOKEN")

    st, pages = call("GET", "/me/accounts?fields=name,instagram_business_account%7Bid,username%7D")
    if st != 200:
        err = pages.get("error", {})
        if err.get("code") == 190:
            done("token_invalid_or_expired", http=st, error=err)
        done("account_lookup_failed", http=st, error=err)
    matches = [p["instagram_business_account"] for p in pages.get("data", [])
               if p.get("instagram_business_account", {}).get("username") == expected_user]
    if len(matches) != 1:
        done("account_not_found_or_ambiguous", expected=expected_user, matches=len(matches))
    uid = matches[0]["id"]
    if expected_id and expected_id != uid:
        done("account_id_mismatch", expected_id=expected_id, found_id=uid)

    try:
        meta = json.load(open(a.metadata))
    except Exception:
        meta = {}
    tags = meta.get("hashtags") or []
    if isinstance(tags, str):
        tags = [t.strip().lstrip("#") for t in tags.split(",") if t.strip()]
    base = (meta.get("title", "") + "\n\n" + meta.get("description", "")).strip()
    # Instagram allows at most 5 hashtags per post; drop YouTube-only tags.
    tags = [t.lstrip("#") for t in tags if t.lstrip("#").lower() not in ("shorts", "youtubeshorts", "ytshorts")][:5]
    if tags:
        base += "\n\n" + " ".join("#" + t for t in tags)
    caption = (a.caption or base)[:2100]

    st, cont = call("POST", f"/{uid}/media", {"media_type": "REELS", "video_url": a.video_url,
                                               "caption": caption, "share_to_feed": "true"})
    cid = cont.get("id")
    if st != 200 or not cid:
        done("container_failed", http=st, error=cont.get("error"))

    status = ""
    for _ in range(40):  # ~10 min max
        time.sleep(15)
        s, r = call("GET", f"/{cid}?fields=status_code,status")
        status = r.get("status_code", "") if s == 200 else "POLL_ERROR"
        print("container status:", status)
        if status in ("FINISHED", "ERROR", "EXPIRED"):
            break
    if status != "FINISHED":
        done("processing_failed", container_status=status, container_id=cid)

    st, pub = call("POST", f"/{uid}/media_publish", {"creation_id": cid})
    mid = pub.get("id", "")
    if st != 200 or not mid:
        done("publish_failed", http=st, error=pub.get("error"), container_id=cid)
    permalink = ""
    s, pl = call("GET", f"/{mid}?fields=permalink")
    if s == 200:
        permalink = pl.get("permalink", "")
    done("published", media_id=mid, url=permalink, container_id=cid, account_id=uid)


if __name__ == "__main__":
    main()
