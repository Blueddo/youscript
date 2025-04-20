import concurrent.futures
import subprocess
from tqdm import tqdm
from termcolor import colored
import os
import urllib.request

# Συνάρτηση ελέγχου διαθεσιμότητας thumbnail
def get_valid_thumbnail(thumbnail_url, video_id):
    if not thumbnail_url:
        return "", "Άγνωστο_Thumbnail"
    
    thumbnails_to_try = [
        thumbnail_url,
        f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
        f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        f"https://i.ytimg.com/vi/{video_id}/sddefault.jpg"
    ]
    
    for thumb_url in thumbnails_to_try:
        try:
            thumb_url = thumb_url.replace(".webp", ".jpg")
            with urllib.request.urlopen(thumb_url) as response:
                if response.getcode() == 200:
                    return thumb_url, os.path.basename(thumb_url)
        except Exception:
            continue
    
    return "", "Άγνωστο_Thumbnail"

# Συνάρτηση φόρτωσης URLs καναλιών από αρχείο
def load_channels():
    channels = []
    try:
        with open("youtube_channels.txt", "r", encoding="utf-8") as file:
            for line in file:
                url = line.strip()
                if url and url.startswith("https://www.youtube.com/"):
                    channels.append(url)
        print(f"Φορτώθηκαν {len(channels)} κανάλια από το αρχείο youtube_channels.txt.")
    except FileNotFoundError:
        print("Το αρχείο youtube_channels.txt δεν βρέθηκε.")
    except Exception as e:
        print(f"Σφάλμα κατά την ανάγνωση του αρχείου: {e}")
    return channels

# Συνάρτηση για λήψη του ονόματος του καναλιού
def get_channel_name(channel_url):
    try:
        result = subprocess.run(
            ["yt-dlp", "--print", "uploader", channel_url],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        uploader = result.stdout.strip()
        if uploader:
            return uploader
        else:
            return "Άγνωστο_Κανάλι"
    except Exception as e:
        print(f"Σφάλμα κατά την εξαγωγή του ονόματος του καναλιού για {channel_url}: {e}")
        return "Άγνωστο_Κανάλι"

# Συνάρτηση για λήψη των URLs των 5 πρώτων βίντεο από ένα κανάλι
def get_channel_videos(channel_url):
    try:
        result = subprocess.run(
            ["yt-dlp", "--get-id", "--playlist-end", "5", channel_url],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        ids = result.stdout.strip().split("\n")
        videos = []

        for video_id in ids:
            if not video_id:
                continue
            
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            # Ελέγξτε αν το βίντεο είναι διαθέσιμο
            availability_check = subprocess.run(
                ["yt-dlp", "-f", "18", "--get-title", video_url],
                capture_output=True, text=True, encoding="utf-8", errors="replace"
            )
            if "members-only" in availability_check.stderr.lower():
                print(f"Παραλείφθηκε το βίντεο {video_id} (μόνο για μέλη).")
                continue
            
            videos.append(video_url)

        return videos
    except Exception as e:
        print(f"Σφάλμα κατά την εξαγωγή των βίντεο για το κανάλι {channel_url}: {e}")
        return []

# Συνάρτηση για λήψη του URL, του τίτλου και του thumbnail του βίντεο
def get_video_info(video_url, channel_name, pbar):
    try:
        video_id = video_url.split("v=")[-1].split("&")[0]

        pbar.set_postfix({"URL": video_id, "Status": "Εξαγωγή τίτλου"})

        title_result = subprocess.run(
            ["yt-dlp", "--get-title", video_url],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        title = title_result.stdout.strip() if title_result.stdout else "Άγνωστος_Τίτλος"
        title = title.replace(" ", "_")

        pbar.set_postfix({"URL": video_id, "Status": "Εξαγωγή thumbnail"})

        try:
            thumbnail_result = subprocess.run(
                ["yt-dlp", "--get-thumbnail", video_url],
                capture_output=True, text=True, encoding="utf-8", errors="replace"
            )
            thumbnail_url = thumbnail_result.stdout.strip() if thumbnail_result.stdout else ""
            valid_thumbnail_url, thumbnail_short = get_valid_thumbnail(thumbnail_url, video_id)
        except (UnicodeDecodeError, subprocess.CalledProcessError) as e:
            valid_thumbnail_url, thumbnail_short = "", "Άγνωστο_Thumbnail_(σφάλμα_εξαγωγής)"
            print(f"Σφάλμα κατά την εξαγωγή thumbnail για {video_url}: {str(e)}")
            pbar.set_postfix({"URL": video_id, "Status": "Σφάλμα thumbnail"})
            return f"Επεξεργασία βίντεο: {video_url} - Σφάλμα thumbnail: {str(e)}"

        pbar.set_postfix({"URL": video_id, "Status": "Εξαγωγή URL"})

        formats_to_try = ["18"]
        output = ""
        used_format = ""
        result = None
        for fmt in formats_to_try:
            try:
                result = subprocess.run(
                    ["yt-dlp", "--get-url", "-f", fmt, video_url],
                    capture_output=True, text=True, encoding="utf-8", errors="replace"
                )
                output = result.stdout.strip()
                if output and output.startswith("https://"):
                    used_format = fmt
                    break
            except (subprocess.CalledProcessError, UnicodeDecodeError) as e:
                print(f"Αποτυχία δοκιμής μορφής {fmt} για {video_url}: {str(e)}")
                continue

        if output:
            status = colored("URL βρέθηκε", "yellow", "on_blue", attrs=["bold", "blink"])
            with open("youtube_videos.m3u", "a") as m3u_file:
                m3u_file.write(f"#EXTINF:-1 group-title=\"{channel_name}\" tvg-logo=\"{valid_thumbnail_url}\",{title}\n")
                m3u_file.write(f"{output}\n")

            print(f"Βίντεο: {video_url}")
            print(f"Τίτλος: {title}")
            print(f"Μορφή: {used_format}")
            print(f"Thumbnail: {thumbnail_short}")
            print(f"Κατάσταση: {status}")
            print("-" * 80)

            pbar.set_postfix({"URL": video_id, "Status": "Ολοκληρώθηκε"})
            return f"Επεξεργασία βίντεο: {video_url} - {status} (μορφή: {used_format}, thumbnail: {thumbnail_short})"
        else:
            error_msg = result.stderr.strip() if result and result.stderr else "Δεν βρέθηκε διαθέσιμη μορφή 18"
            pbar.set_postfix({"URL": video_id, "Status": "Σφάλμα URL"})
            print(f"Βίντεο: {video_url}")
            print(f"Σφάλμα: {error_msg}")
            print("-" * 80)
            return f"Επεξεργασία βίντεο: {video_url} - δεν βρέθηκε έγκυρο URL: {error_msg}"
    except Exception as e:
        pbar.set_postfix({"URL": video_id, "Status": "Γενικό σφάλμα"})
        print(f"Βίντεο: {video_url}")
        print(f"Σφάλμα: {str(e)}")
        print("-" * 80)
        return f"Σφάλμα κατά την επεξεργασία του βίντεο {video_url}: {e}"

# Κύριο πρόγραμμα
channels = load_channels()
video_list = []
for channel in channels:
    channel_name = get_channel_name(channel)
    videos = get_channel_videos(channel)
    for video in videos:
        video_list.append((video, channel_name))

with open("youtube_videos.m3u", "w") as m3u_file:
    m3u_file.write("#EXTM3U\n")

if video_list:
    with tqdm(total=len(video_list), desc="Επεξεργασία βίντεο YouTube", ncols=120, bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} {postfix}') as pbar:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(get_video_info, video, channel_name, pbar) for video, channel_name in video_list]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
            for result in results:
                pbar.update(1)
                print(result)
else:
    print("Δεν υπάρχουν βίντεο για επεξεργασία.")
