import concurrent.futures
import subprocess
import sys
import os
from tqdm import tqdm
from termcolor import colored

# Συνάρτηση για εγκατάσταση εξαρτήσεων
def install_dependencies():
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "tqdm", "termcolor", "yt-dlp"])
        print("Εγκαταστάθηκαν όλες οι εξαρτήσεις.")
    except subprocess.CalledProcessError as e:
        print(f"Σφάλμα κατά την εγκατάσταση εξαρτήσεων: {e}")
        sys.exit(1)

# Συνάρτηση φόρτωσης χρηστών από αρχείο
def load_users():
    users = []
    file_path = "usersyoutube.txt"
    if not os.path.exists(file_path):
        print(colored(f"Το αρχείο {file_path} δεν βρέθηκε!", "red"))
        sys.exit(1)
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            for line in file:
                user = line.strip()
                if user:
                    users.append(user)
        if not users:
            print(colored("Το αρχείο usersyoutube.txt είναι κενό!", "red"))
            sys.exit(1)
        print(f"Φορτώθηκαν {len(users)} χρήστες από το αρχείο {file_path}.")
    except Exception as e:
        print(f"Σφάλμα κατά την ανάγνωση του αρχείου: {e}")
        sys.exit(1)
    return users

# Συνάρτηση ανάκτησης βίντεο από το κανάλι
def check_user_videos(user):
    try:
        # Εκτέλεση yt-dlp με επιλογές για να αποφύγουμε μπλοκάρισμα
        cmd = [
            "yt-dlp",
            "-f", "18",  # Ποιότητα 360p
            "--get-url",
            "--get-title",
            "--playlist-end", "5",
            "--no-check-certificates",  # Παράλειψη ελέγχου πιστοποιητικών
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            f"https://www.youtube.com/{user}/videos"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True, text=True, check=True
        )
        output = result.stdout.strip().splitlines()

        if output:
            videos = []
            for i in range(0, len(output), 2):
                if i + 1 < len(output):
                    title = output[i].strip()
                    url = output[i + 1].strip()
                    if url.startswith("https://"):
                        videos.append((title, url))

            if videos:
                status = colored(f"Βρέθηκαν {len(videos)} βίντεο (ποιότητα 360p)", "green", attrs=["bold"])
                with open("youtube_videos.m3u", "a", encoding="utf-8") as m3u_file:
                    for title, url in videos:
                        m3u_file.write(f"#EXTINF:-1 group-title=\"YouTube Videos\" tvg-logo=\"https://www.youtube.com/favicon.ico\" tvg-id=\"simpleTVFakeEpgId\" $ExtFilter=\"YouTube Videos\",{user} - {title}\n")
                        m3u_file.write(f"{url}\n")
                return f"Έλεγχος χρήστη: {user} - {status}"
            else:
                return f"Έλεγχος χρήστη: {user} - Δεν βρέθηκαν προσβάσιμα βίντεο"
        else:
            return f"Έλεγχος χρήστη: {user} - Δεν βρέθηκαν βίντεο"
    except subprocess.CalledProcessError as e:
        error_message = e.stderr.strip()
        if "Sign in to confirm" in error_message or "members-only" in error_message:
            return f"Έλεγχος χρήστη: {user} - Παραλείφθηκε λόγω περιορισμών πρόσβασης (σύνδεση ή members-only)"
        return f"Έλεγχος χρήστη: {user} - Σφάλμα yt-dlp: {error_message}"
    except Exception as e:
        return f"Σφάλμα κατά τον έλεγχο του χρήστη {user}: {e}"

# Κύριο πρόγραμμα
def main():
    # Εγκατάσταση εξαρτήσεων
    install_dependencies()

    # Φόρτωση χρηστών
    users = load_users()

    # Δημιουργία αρχείου m3u
    with open("youtube_videos.m3u", "w", encoding="utf-8") as m3u_file:
        m3u_file.write("#EXTM3U $BorpasFileFormat=\"1\" $NestedGroupsSeparator=\"/\"\n")

    # Έλεγχος χρηστών με παράλληλη εκτέλεση
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(tqdm(
            executor.map(check_user_videos, users),
            total=len(users),
            desc="Έλεγχος χρηστών του YouTube για βίντεο",
            ncols=120,
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} {postfix}'
        ))
        for result in results:
            tqdm.write(result)

if __name__ == "__main__":
    main()
