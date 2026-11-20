#!/usr/bin/env python3
"""Upload a video to YouTube as private using a stored OAuth refresh token.

Stdlib only. Reads YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN from env.
Usage: upload_youtube.py --file VIDEO.mp4 --metadata metadata.json --privacy private
Writes youtube_result.json next to the metadata file and prints the video URL.
"""
import argparse, json, os, sys, urllib.request, urllib.parse, urllib.error

def post_form(url, data):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(),
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--metadata", required=True)
    ap.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    a = ap.parse_args()
    cid = os.environ.get("YT_CLIENT_ID", "").strip()
    secret = os.environ.get("YT_CLIENT_SECRET", "").strip()
    rtok = os.environ.get("YT_REFRESH_TOKEN", "").strip()
    result_path = os.path.join(os.path.dirname(os.path.abspath(a.metadata)), "youtube_result.json")

    def record(status, **kw):
        with open(result_path, "w") as f:
            json.dump({"status": status, **kw}, f, indent=2)
        print(json.dumps({"status": status, **kw}))

    if not (cid and secret and rtok):
        record("skipped", reason="missing secrets")
        return 0
    meta = json.load(open(a.metadata))
    title = (meta.get("title") or "Untitled").strip()[:100]
    desc = (meta.get("description") or "").strip()
    tags = meta.get("hashtags") or []
    if isinstance(tags, str):
        tags = [t.strip().lstrip("#") for t in tags.split(",") if t.strip()]
    if tags:
        desc = (desc + "\n\n" + " ".join("#" + t for t in tags[:15])).strip()
    try:
        tok = post_form("https://oauth2.googleapis.com/token", {
            "client_id": cid, "client_secret": secret,
            "refresh_token": rtok, "grant_type": "refresh_token"})
        access = tok["access_token"]
    except Exception as e:
        record("failed", stage="token_refresh", error=str(e)[:500])
        return 1
    body = {"snippet": {"title": title, "description": desc, "tags": tags[:15]},
            "status": {"privacyStatus": a.privacy, "madeForKids": False, "selfDeclaredMadeForKids": False}}
    init = urllib.request.Request(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": "Bearer " + access,
                 "Content-Type": "application/json; charset=UTF-8",
                 "X-Upload-Content-Type": "video/mp4",
                 "X-Upload-Content-Length": str(os.path.getsize(a.file))})
    try:
        with urllib.request.urlopen(init, timeout=60) as r:
            upload_url = r.headers["Location"]
    except urllib.error.HTTPError as e:
        record("failed", stage="initiate", error=(str(e) + " " + e.read().decode()[:400])[:500])
        return 1
    put = urllib.request.Request(upload_url, data=open(a.file, "rb").read(), method="PUT",
                                 headers={"Content-Type": "video/mp4"})
    try:
        with urllib.request.urlopen(put, timeout=600) as r:
            resp = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        record("failed", stage="upload", error=(str(e) + " " + e.read().decode()[:400])[:500])
        return 1
    vid = resp.get("id", "")
    record("uploaded", video_id=vid, url=("https://youtu.be/" + vid) if vid else "",
           privacy=a.privacy, title=title)
    return 0

if __name__ == "__main__":
    sys.exit(main())

