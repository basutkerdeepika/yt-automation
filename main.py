import os
import subprocess
import instaloader
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# IG_USERNAME = os.getenv("IG_USERNAME")
# IG_PASSWORD = os.getenv("IG_PASSWORD")

IG_USERNAME = "idyllic___soul"
# IG_PASSWORD = "Deep@jay7795!"

YT_CLIENT_ID = os.getenv("YT_CLIENT_ID")
YT_CLIENT_SECRET = os.getenv("YT_CLIENT_SECRET")
YT_REFRESH_TOKEN = os.getenv("YT_REFRESH_TOKEN")

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

DOWNLOAD_DIR = "downloads"
PROCESSED_FILE = "processed.txt"


# ----------------------------
# Processed tracking
# ----------------------------

def load_processed():
    if not os.path.exists(PROCESSED_FILE):
        return set()
    with open(PROCESSED_FILE) as f:
        return set(f.read().splitlines())


def save_processed(shortcode):
    with open(PROCESSED_FILE, "a") as f:
        f.write(shortcode + "\n")


# ----------------------------
# Video analysis
# ----------------------------

def get_video_info(path):
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,duration",
        "-of", "default=noprint_wrappers=1",
        path,
    ]

    result = subprocess.check_output(cmd).decode()

    width = height = duration = 0

    for line in result.splitlines():
        if "width=" in line:
            width = int(line.split("=")[1])
        elif "height=" in line:
            height = int(line.split("=")[1])
        elif "duration=" in line:
            try:
                duration = float(line.split("=")[1])
            except:
                duration = 0

    return width, height, duration


def is_short(width, height, duration):
    return height > width and duration <= 60


# ----------------------------
# Instagram
# ----------------------------

# def login_instagram():
#     L = instaloader.Instaloader(
#         download_video_thumbnails=False,
#         save_metadata=False,
#         dirname_pattern=DOWNLOAD_DIR,
#     )
#     L.login(IG_USERNAME, IG_PASSWORD)
#     return L

def login_instagram():
    L = instaloader.Instaloader(
        download_video_thumbnails=False,
        save_metadata=False,
        dirname_pattern=DOWNLOAD_DIR,
    )
    return L


def download_videos(loader):
    profile = instaloader.Profile.from_username(loader.context, IG_USERNAME)
    processed = load_processed()
    new_posts = []

    for post in profile.get_posts():
        if post.is_video and post.shortcode not in processed:
            loader.download_post(post, target=IG_USERNAME)
            new_posts.append((post.shortcode, post.caption or ""))

    return new_posts


# ----------------------------
# YouTube (HEADLESS)
# ----------------------------

def get_youtube_service():
    creds = Credentials(
        None,
        refresh_token=YT_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=YT_CLIENT_ID,
        client_secret=YT_CLIENT_SECRET,
        scopes=SCOPES,
    )

    creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)


def upload_video(youtube, file_path, title, description):
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title[:100],
                "description": description,
                "categoryId": "22",
            },
            "status": {"privacyStatus": "public"},
        },
        media_body=MediaFileUpload(file_path),
    )
    request.execute()


# ----------------------------
# Main
# ----------------------------

def main():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    loader = login_instagram()
    new_posts = download_videos(loader)

    if not new_posts:
        print("No new videos")
        return

    youtube = get_youtube_service()

    for shortcode, caption in new_posts:
        for root, _, files in os.walk(DOWNLOAD_DIR):
            for file in files:
                if file.endswith(".mp4") and shortcode in file:
                    path = os.path.join(root, file)

                    width, height, duration = get_video_info(path)
                    short_flag = is_short(width, height, duration)

                    if short_flag:
                        title = (caption[:70] or "Instagram Short") + " #Shorts"
                        description = f"""
Original: https://www.instagram.com/{IG_USERNAME}/
Credit: @{IG_USERNAME}

{caption}

#Shorts #instagram
"""
                    else:
                        title = caption[:80] or "Instagram Upload"
                        description = f"""
Original: https://www.instagram.com/{IG_USERNAME}/
Credit: @{IG_USERNAME}

{caption}
"""

                    upload_video(youtube, path, title, description)
                    save_processed(shortcode)


if __name__ == "__main__":
    main()
