import concurrent.futures
import subprocess
from tqdm import tqdm
from termcolor import colored
import os
import urllib.request
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
        if result.stderr:
            print(f"Σφάλματα yt-dlp (uploader) για {channel_url}:\n{result.stderr}")
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
        # Προσθήκη /videos για περιορισμό στην καρτέλα Videos (ή αφαίρεσε για Videos, Live, Shorts)
        channel_url = f"{channel_url}/videos"
        # Εκτέλεση της εντολής με -f 18 για να ταιριάζει με την εντολή σου
        result = subprocess.run(
            ["yt-dlp", "-f", "18", "--get-id", "--playlist-end", "5", channel_url],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        # Εκτύπωση εξόδου και σφαλμάτων για διάγνωση
        if result.stdout:
            print(f"Εξήχθησαν IDs για {channel_url}:\n{result.stdout}")
        if result.stderr:
            print(f"Σφάλματα yt-dlp για {channel_url}:\n{result.stderr}")
        
        # Έλεγχος κωδικού επιστροφής
        if result.returncode != 0:
            print(f"Η εντολή yt-dlp απέτυχε για {channel_url} με κωδικό {result.returncode}")
            return []
        
        # Εξαγωγή IDs
        ids = result.stdout.strip().split("\n")
        videos = []
        for video_id in ids:
            if not video_id:
                continue
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            # Έλεγχος διαθεσιμότητας
            availability_check = subprocess.run(
                ["yt-dlp", "-f", "18/best", "--get-title", video_url],
                capture_output=True, text=True, encoding="utf-8", errors="replace"
            )
            if "members-only" in availability_check.stderr.lower():
                print(f"Παραλείφθηκε το βίντεο {video_id} (μόνο για μέλη).")
                continue
            if availability_check.returncode == 0 and availability_check.stdout:
                videos.append(video_url)
            else:
                print(f"Το βίντεο {video_id} δεν είναι διαθέσιμο: {availability_check.stderr}")
        print(f"Βρέθηκαν {len(videos)} διαθέσιμα βίντεο για {channel_url}")
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
        if title_result.stderr:
            print(f"Σφάλματα yt-dlp (τίτλος) για {video_url}:\n{title_result.stderr}")
        title = title_result.stdout.strip() if title_result.stdout else "Άγνωστος_Τίτλος"
        title = title.replace(" ", "_")

        pbar.set_postfix({"URL": video_id, "Status": "Εξαγωγή thumbnail"})

        try:
            thumbnail_result = subprocess.run(
                ["yt-dlp", "--get-thumbnail", video_url],
                capture_output=True, text=True, encoding="utf-8", errors="replace"
            )
            if thumbnail_result.stderr:
                print(f"Σφάλματα yt-dlp (thumbnail) για {video_url}:\n{thumbnail_result.stderr}")
            thumbnail_url = thumbnail_result.stdout.strip() if thumbnail_result.stdout else ""
            valid_thumbnail_url, thumbnail_short = get_valid_thumbnail(thumbnail_url, video_id)
        except (UnicodeDecodeError, subprocess.CalledProcessError) as e:
            valid_thumbnail_url, thumbnail_short = "", "Άγνωστο_Thumbnail_(σφάλμα_εξαγωγής)"
            print(f"Σφάλμα κατά την εξαγωγή thumbnail για {video_url}: {str(e)}")
            pbar.set_postfix({"URL": video_id, "Status": "Σφάλμα thumbnail"})
            return f"Επεξεργασία βίντεο: {video_url} - Σφάλμα thumbnail: {str(e)}"

        pbar.set_postfix({"URL": video_id, "Status": "Εξαγωγή URL"})

        formats_to_try = ["18", "best"]  # Δοκιμή μορφής 18, μετά best
        output = ""
        used_format = ""
        result = None
        for fmt in formats_to_try:
            try:
                result = subprocess.run(
                    ["yt-dlp", "--get-url", "-f", fmt, video_url],
                    capture_output=True, text=True, encoding="utf-8", errors="replace"
                )
                if result.stderr:
                    print(f"Σφάλματα yt-dlp (URL, μορφή {fmt}) για {video_url}:\n{result.stderr}")
                output = result.stdout.strip()
                if output and output.startswith("https://"):
                    used_format = fmt
                    break
            except (subprocess.CalledProcessError, UnicodeDecodeError) as e:
                print(f"Αποτυχία δοκιμής μορφής {fmt} για {video_url}: {str(e)}")
                continue

        if output:
            status = colored("URL βρέθηκε", "yellow", "on_blue", attrs=["bold", "blink"])
            with open("youtube_videos.m3u", "a", encoding="utf-8") as m3u_file:
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
            error_msg = result.stderr.strip() if result and result.stderr else "Δεν βρέθηκε διαθέσιμη μορφή"
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
def main():
    channels = load_channels()
    video_list = []
    for channel in channels:
        channel_name = get_channel_name(channel)
        videos = get_channel_videos(channel)
        for video in videos:
            video_list.append((video, channel_name))
        time.sleep(1)  # Καθυστέρηση 1 δευτερολέπτου για αποφυγή rate limiting

    # Δημιουργία αρχείου M3U
    with open("youtube_videos.m3u", "w", encoding="utf-8") as m3u_file:
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

if __name__ == "__main__":
    main()
