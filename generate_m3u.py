import concurrent.futures
import subprocess
from tqdm import tqdm
from termcolor import colored
import os
import urllib.request
import sys
import time

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

# Συνάρτηση φόρτωσης URLs καναλιών από το αρχείο
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
        print(colored("Το αρχείο youtube_channels.txt δεν βρέθηκε.", "red"))
    except Exception as e:
        print(colored(f"Σφάλμα κατά την ανάγνωση του αρχείου: {e}", "red"))
    return channels

# Συνάρτηση για λήψη του ονόματος του καναλιού
def get_channel_name(channel_url):
    print(f"Προσπάθεια εξαγωγής ονόματος για το κανάλι: {channel_url}")
    try:
        result = subprocess.run(
            ["yt-dlp", "--print", "uploader", "--no-warnings", "--force-ipv4", channel_url],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=120
        )
        print(f"Κωδικός εξόδου: {result.returncode}")
        print(f"stdout: {result.stdout.strip()}")
        print(f"stderr: {result.stderr.strip()}")

        uploader = result.stdout.strip()
        if result.returncode == 0 and uploader:
            print(f"Επιτυχής εξαγωγή ονόματος: {uploader}")
            return uploader
        else:
            print(colored(f"Δεν βρέθηκε όνομα καναλιού για {channel_url}: {result.stderr}", "red"))
            return "Άγνωστο_Κανάλι"
    except subprocess.TimeoutExpired:
        print(colored(f"Η εντολή yt-dlp για {channel_url} έληξε λόγω timeout.", "red"))
        return "Άγνωστο_Κανάλι"
    except Exception as e:
        print(colored(f"Γενικό σφάλμα για το κανάλι {channel_url}: {e}", "red"))
        return "Άγνωστο_Κανάλι"

# Συνάρτηση για λήψη των URLs των 5 πρώτων βίντεο από την καρτέλα Videos
def get_channel_videos(channel_url):
    print(f"Προσπάθεια εξαγωγής βίντεο για το κανάλι: {channel_url}")
    try:
        videos_url = channel_url.rstrip("/") + "/videos"
        result = subprocess.run(
            ["yt-dlp", "--get-id", "--playlist-end", "5", "--no-warnings", "--force-ipv4", videos_url],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=120
        )
        print(f"Κωδικός εξόδου: {result.returncode}")
        print(f"stdout: {result.stdout.strip()}")
        print(f"stderr: {result.stderr.strip()}")

        ids = result.stdout.strip().split("\n")
        videos = [f"https://www.youtube.com/watch?v={video_id}" for video_id in ids if video_id]
        print(f"Βρέθηκαν {len(videos)} βίντεο για το κανάλι {channel_url}")
        return videos
    except subprocess.TimeoutExpired:
        print(colored(f"Η εξαγωγή βίντεο για {channel_url} έληξε λόγω timeout.", "red"))
        return []
    except Exception as e:
        print(colored(f"Σφάλμα εξαγωγής βίντεο για {channel_url}: {e}", "red"))
        return []

# Συνάρτηση για λήψη του URL, του τίτλου και του thumbnail του βίντεο
def get_video_info(video_url, channel_name, pbar):
    try:
        video_id = video_url.split("v=")[-1].split("&")[0]
        pbar.set_postfix({"URL": video_id, "Status": "Εξαγωγή τίτλου"})

        title_result = subprocess.run(
            ["yt-dlp", "--get-title", "--no-warnings", "--force-ipv4", video_url],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=60
        )
        print(f"Τίτλος βίντεο {video_id} - Κωδικός εξόδου: {title_result.returncode}")
        print(f"stderr: {title_result.stderr.strip()}")
        title = title_result.stdout.strip() if title_result.stdout else "Άγνωστος_Τίτλος"

        pbar.set_postfix({"URL": video_id, "Status": "Εξαγωγή thumbnail"})
        thumbnail_result = subprocess.run(
            ["yt-dlp", "--get-thumbnail", "--no-warnings", "--force-ipv4", video_url],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=60
        )
        print(f"Thumbnail βίντεο {video_id} - Κωδικός εξόδου: {thumbnail_result.returncode}")
        print(f"stderr: {thumbnail_result.stderr.strip()}")
        thumbnail_url = thumbnail_result.stdout.strip() if thumbnail_result.stdout else ""
        valid_thumbnail_url, thumbnail_short = get_valid_thumbnail(thumbnail_url, video_id)

        pbar.set_postfix({"URL": video_id, "Status": "Εξαγωγή URL"})
        result = subprocess.run(
            ["yt-dlp", "-f", "18", "--get-url", "--no-warnings", "--force-ipv4", video_url],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=60
        )
        print(f"URL βίντεο {video_id} - Κωδικός εξόδου: {result.returncode}")
        print(f"stderr: {result.stderr.strip()}")
        output = result.stdout.strip()

        if output and output.startswith("https://"):
            with open("youtube_videos.m3u", "a", encoding="utf-8") as m3u_file:
                m3u_file.write(f"#EXTINF:-1 group-title=\"{channel_name}\" tvg-logo=\"{valid_thumbnail_url}\",{title}\n")
                m3u_file.write(f"{output}\n")
            pbar.set_postfix({"URL": video_id, "Status": "Ολοκληρώθηκε"})
            return f"Επεξεργασία βίντεο: {video_url} - URL βρέθηκε"
        else:
            pbar.set_postfix({"URL": video_id, "Status": "Σφάλμα URL"})
            return f"Επεξεργασία βίντεο: {video_url} - δεν βρέθηκε έγκυρο URL: {result.stderr}"
    except subprocess.TimeoutExpired:
        pbar.set_postfix({"URL": video_id, "Status": "Timeout"})
        return f"Επεξεργασία βίντεο: {video_url} - έληξε λόγω timeout"
    except Exception as e:
        pbar.set_postfix({"URL": video_id, "Status": "Γενικό σφάλμα"})
        return f"Σφάλμα κατά την επεξεργασία του βίντεο {video_url}: {e}"

# Κύριο πρόγραμμα
def main():
    print("Έναρξη προγράμματος...")
    channels = load_channels()
    if not channels:
        print(colored("Κανένα κανάλι δεν φορτώθηκε. Ελέγξτε το youtube_channels.txt.", "red"))
        return

    video_list = []
    for channel in channels:
        print(f"\nΕπεξεργασία καναλιού: {channel}")
        try:
            channel_name = get_channel_name(channel)
            print(f"Όνομα καναλιού: {channel_name}")
            videos = get_channel_videos(channel)
            for video in videos:
                video_list.append((video, channel_name))
            time.sleep(2)  # Καθυστέρηση 2 δευτερολέπτων μεταξύ καναλιών
        except Exception as e:
            print(colored(f"Σφάλμα κατά την επεξεργασία του καναλιού {channel}: {e}", "red"))

    if not video_list:
        print(colored("Δεν βρέθηκαν βίντεο για επεξεργασία.", "red"))
        return

    print(f"Συνολικά βίντεο προς επεξεργασία: {len(video_list)}")
    
    with open("youtube_videos.m3u", "w", encoding="utf-8") as m3u_file:
        m3u_file.write("#EXTM3U\n")

    with tqdm(total=len(video_list), desc="Επεξεργασία βίντεο YouTube", ncols=120, 
              bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{percentage:.1f}%] {postfix}') as pbar:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(get_video_info, video, channel_name, pbar) for video, channel_name in video_list]
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    pbar.update(1)
                    print(result)
                except Exception as e:
                    print(colored(f"Σφάλμα κατά την επεξεργασία βίντεο: {e}", "red"))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(colored(f"Κρίσιμο σφάλμα στο πρόγραμμα: {e}", "red"))
