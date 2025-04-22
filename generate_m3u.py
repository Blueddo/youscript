import concurrent.futures
import subprocess
from tqdm import tqdm
from termcolor import colored

# Συνάρτηση φόρτωσης χρηστών από αρχείο
def load_users():
    users = []
    try:
        with open("usersyoutube.txt", "r") as file:
            for line in file:
                user = line.strip()
                if user.startswith("@"):
                    user = user[1:]  # Αφαίρεση του '@'
                users.append(user)
        print(f"Φορτώθηκαν {len(users)} χρήστες από το αρχείο usersyoutube.txt.")
    except FileNotFoundError:
        print("Το αρχείο usersyoutube.txt δεν βρέθηκε.")
    except Exception as e:
        print(f"Σφάλμα κατά την ανάγνωση του αρχείου: {e}")
    return users

# Συνάρτηση ανάκτησης βίντεο από το κανάλι
def check_user_videos(user):
    try:
        # Εκτέλεση yt-dlp για να πάρουμε τη λίστα των πιο πρόσφατων βίντεο από το κανάλι
        result = subprocess.run(
            ["yt-dlp", "-f", "18", "--get-url", "--get-title", "--playlist-end", "5", f"https://www.youtube.com/{user}/videos"],
            capture_output=True, text=True
        )
        output = result.stdout.strip().splitlines()

        if output:
            # Διαχωρισμός τίτλων και URLs (ο yt-dlp επιστρέφει τίτλο και μετά URL για κάθε βίντεο)
            videos = []
            for i in range(0, len(output), 2):
                if i + 1 < len(output):  # Βεβαιωνόμαστε ότι υπάρχει URL μετά τον τίτλο
                    title = output[i].strip()
                    url = output[i + 1].strip()
                    if url.startswith("https://"):
                        videos.append((title, url))

            if videos:
                status = colored(f"βρέθηκαν {len(videos)} βίντεο (ποιότητα 360p)", "green", attrs=["bold"])
                with open("youtube_videos.m3u", "a") as m3u_file:
                    for title, url in videos:
                        m3u_file.write(f"#EXTINF:-1 group-title=\"YouTube Videos\" tvg-logo=\"https://www.youtube.com/favicon.ico\" tvg-id=\"simpleTVFakeEpgId\" $ExtFilter=\"YouTube Videos\",{user} - {title}\n")
                        m3u_file.write(f"{url}\n")
                return f"Έλεγχος χρήστη: {user} - {status}"
            else:
                return f"Έλεγχος χρήστη: {user} - δεν βρέθηκαν βίντεο"
        else:
            return f"Έλεγχος χρήστη: {user} - δεν βρέθηκαν βίντεο"
    except subprocess.CalledProcessError:
        return f"Έλεγχος χρήστη: {user} - σφάλμα κατά την ανάκτηση βίντεο"
    except Exception as e:
        return f"Σφάλμα κατά τον έλεγχο του χρήστη {user}: {e}"

# Φόρτωση χρηστών από το αρχείο
users = load_users()

# Δημιουργία αρχείου m3u με επιπλέον πληροφορίες
with open("youtube_videos.m3u", "w") as m3u_file:
    m3u_file.write("#EXTM3U $BorpasFileFormat=\"1\" $NestedGroupsSeparator=\"/\"\n")

# Έλεγχος για κάθε χρήστη για βίντεο με παράλληλη εκτέλεση
with concurrent.futures.ThreadPoolExecutor() as executor:
    results = list(tqdm(executor.map(check_user_videos, users), total=len(users), desc="Έλεγχος χρηστών του YouTube για βίντεο", ncols=120, bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} {postfix}'))
    for result in results:
        tqdm.write(result)
