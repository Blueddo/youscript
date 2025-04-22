import concurrent.futures
import subprocess
import time
from tqdm import tqdm
from termcolor import colored

def load_users():
    users = []
    try:
        with open("usersyoutube.txt", "r", encoding="utf-8") as file:
            for line in file:
                user = line.strip().lstrip('@')  # Αφαίρεση του @ αν υπάρχει
                users.append(user)
        print(f"Φορτώθηκαν {len(users)} χρήστες από το αρχείο usersyoutube.txt.")
    except FileNotFoundError:
        print("Το αρχείο usersyoutube.txt δεν βρέθηκε.")
    except Exception as e:
        print(f"Σφάλμα κατά την ανάγνωση του αρχείου: {e}")
    return users

def check_user_videos(user):
    try:
        if not user:
            return f"Έλεγχος χρήστη: {user} - κενό όνομα χρήστη"
        
        time.sleep(2)
        url_formats = [
            f"https://www.youtube.com/@{user}/videos",
            f"https://www.youtube.com/c/{user}/videos",
            f"https://www.youtube.com/user/{user}/videos"
        ]
        
        for url in url_formats:
            print(f"Checking URL: {url}")
            result = subprocess.run(
                ["yt-dlp", "-f", "18", "--get-url", "--get-title", "--playlist-end", "5", "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124", url],
                capture_output=True, text=True
            )
            print(f"yt-dlp stdout for {user}: {result.stdout}")
            print(f"yt-dlp stderr for {user}: {result.stderr}")
            
            if result.returncode == 0 and result.stdout.strip():
                output = result.stdout.strip().splitlines()
                break
        else:
            return f"Έλεγχος χρήστη: {user} - κανένα έγκυρο URL δεν βρέθηκε"

        if output:
            videos = []
            for i in range(0, len(output), 2):
                if i + 1 < len(output):
                    title = output[i].strip()
                    url = output[i + 1].strip()
                    if url.startswith("https://"):
                        videos.append((title, url))

            if videos:
                status = colored(f"βρέθηκαν {len(videos)} βίντεο (ποιότητα 360p)", "green", attrs=["bold"])
                with open("youtube_videos.m3u", "a", encoding="utf-8") as m3u_file:
                    for title, url in videos:
                        m3u_file.write(f"#EXTINF:-1 group-title=\"YouTube Videos\" tvg-logo=\"https://www.youtube.com/favicon.ico\" tvg-id=\"simpleTVFakeEpgId\" $ExtFilter=\"YouTube Videos\",{user} - {title}\n")
                        m3u_file.write(f"{url}\n")
                return f"Έλεγχος χρήστη: {user} - {status}"
            else:
                return f"Έλεγχος χρήστη: {user} - δεν βρέθηκαν βίντεο"
        else:
            return f"Έλεγχος χρήστη: {user} - δεν βρέθηκαν βίντεο"
    except subprocess.CalledProcessError as e:
        return f"Έλεγχος χρήστη: {user} - σφάλμα κατά την ανάκτηση βίντεο: {e.stderr}"
    except Exception as e:
        return f"Σφάλμα κατά τον έλεγχο του χρήστη {user}: {e}"

users = load_users()

with open("youtube_videos.m3u", "w", encoding="utf-8") as m3u_file:
    m3u_file.write("#EXTM3U $BorpasFileFormat=\"1\" $NestedGroupsSeparator=\"/\"\n")

with concurrent.futures.ThreadPoolExecutor() as executor:
    results = list(tqdm(executor.map(check_user_videos, users), total=len(users), desc="Έλεγχος χρηστών του YouTube για βίντεο", ncols=120, bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} {postfix}'))
    for result in results:
        tqdm.write(result)
