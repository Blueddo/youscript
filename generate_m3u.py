import subprocess
import re

def get_youtube_playlist_info(url, max_videos=5):
    # Command to get title and URL for each video
    command = [
        'yt-dlp',
        '-f', '18',  # Select format (360p mp4)
        '--get-url',
        '--get-title',
        '--playlist-end', str(max_videos),
        url
    ]
    
    try:
        # Execute command and capture output
        output = subprocess.check_output(command, text=True)
        lines = output.strip().split('\n')
        
        # Pair titles with URLs
        videos = []
        for i in range(0, len(lines), 2):
            if i + 1 < len(lines):
                title = re.sub(r'[^\w\s-]', '', lines[i]).strip()  # Clean title
                url = lines[i + 1].strip()
                videos.append((title, url))
        return videos
    except subprocess.CalledProcessError as e:
        print(f"Error running yt-dlp: {e}")
        return []

def create_m3u_playlist(videos, output_file="playlist.m3u"):
    # Create M3U content
    m3u_content = "#EXTM3U\n"
    for title, url in videos:
        m3u_content += f"#EXTINF:-1,{title}\n{url}\n"
    
    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(m3u_content)
    print(f"M3U playlist saved as {output_file}")

if __name__ == "__main__":
    playlist_url = "https://www.youtube.com/@grxpress/videos"
    videos = get_youtube_playlist_info(playlist_url, max_videos=5)
    if videos:
        create_m3u_playlist(videos)
