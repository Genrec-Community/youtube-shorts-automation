#!/usr/bin/env python3
"""Publish a Reel to Instagram via the Instagram Platform API (Instagram Login setup).

Needs env IG_USER_ID and IG_ACCESS_TOKEN (long-lived Instagram User token with
instagram_business_basic + instagram_business_content_publish). Meta fetches the
video from --video-url, which must be publicly reachable at publish time.

Usage: upload_instagram.py --video-url URL --metadata metadata.json
Writes instagram_result.json next to the metadata file.
"""
import argparse, json, os, sys, time, urllib.parse, urllib.request

API = "https://graph.instagram.com/v23.0"

def req(method, url, data=None):
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    r = urllib.request.Request(url, data=body, method=method)
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read().decode())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video-url", required=True)
    ap.add_argument("--metadata", required=True)
    ap.add_argument("--caption", default="")
    a = ap.parse_args()
    uid = os.environ.get("IG_USER_ID", "")
    tok = os.environ.get("IG_ACCESS_TOKEN", "")
    out_path = os.path.join(os.path.dirname(os.path.abspath(a.metadata)), "instagram_result.json")

    def done(status, **extra):
        json.dump({"status": status, **extra}, open(out_path, "w"))
        print("instagram:", status, extra)
        sys.exit(0 if status in ("published",) else 1)

    if not uid or not tok:
        done("skipped", reason="missing IG_USER_ID or IG_ACCESS_TOKEN")

    try:
        meta = json.load(open(a.metadata))
    except Exception:
        meta = {}
    tags = meta.get("hashtags") or []
    if isinstance(tags, str):
        tags = [t.strip().lstrip("#") for t in tags.split(",") if t.strip()]
    base = (meta.get("title", "") + "\n\n" + meta.get("description", "")).strip()
    if tags:
        base += "\n\n" + " ".join("#" + t for t in tags[:15])
    caption = a.caption or base
    caption = caption[:2100]

    try:
        cont = req("POST", f"{API}/{uid}/media", {
            "media_type": "REELS",
            "video_url": a.video_url,
            "caption": caption,
            "share_to_feed": "true",
            "access_token": tok,
        })
    except Exception as e:
        done("container_failed", error=str(e)[:500])
    cid = cont.get("id")
    if not cid:
        done("container_failed", response=cont)

    status = ""
    for _ in range(40):  # ~10 min max
        time.sleep(15)
        try:
            st = req("GET", f"{API}/{cid}?fields=status_code&access_token={urllib.parse.quote(tok)}")
            status = st.get("status_code", "")
        except Exception as e:
            status = "POLL_ERROR:" + str(e)[:200]
        print("container status:", status)
        if status in ("FINISHED", "ERROR", "EXPIRED"):
            break
    if status != "FINISHED":
        done("processing_failed", container_status=status, container_id=cid)

    try:
        pub = req("POST", f"{API}/{uid}/media_publish", {"creation_id": cid, "access_token": tok})
    except Exception as e:
        done("publish_failed", error=str(e)[:500], container_id=cid)
    mid = pub.get("id", "")
    permalink = ""
    if mid:
        try:
            pl = req("GET", f"{API}/{mid}?fields=permalink&access_token={urllib.parse.quote(tok)}")
            permalink = pl.get("permalink", "")
        except Exception:
            pass
    done("published", media_id=mid, url=permalink, container_id=cid)

if __name__ == "__main__":
    main()
