import os
import urllib.request

# The only file you need to output
output_file = os.path.join(".", "family_safe.m3u")

# The list of category URLs you want to pull from
SOURCE_URLS = [
    "https://iptv-org.github.io/iptv/categories/sports.m3u",
    "https://raw.githubusercontent.com/doms9/iptv/refs/heads/default/M3U8/events.m3u8",
    "https://raw.githubusercontent.com/doms9/iptv/refs/heads/default/M3U8/TV.m3u8",
    "https://raw.githubusercontent.com/Love4vn/Match_Stream/refs/heads/1/live_schedule_Optimize.m3u",
    "https://raw.githubusercontent.com/kadirsener1/247/refs/heads/main/tv247_bite.m3u",
    "https://raw.githubusercontent.com/Tahir2020/TR_Avrupa/refs/heads/main/playlist/playerlist.m3u",
]

def build_master_list():
    print("Starting clean compilation...")
    # Add the single required header to the top of the file
    combined_lines = ["#EXTM3U\n"]
    
    for url in SOURCE_URLS:
        print(f"Fetching: {url}")
        try:
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req) as response:
                content = response.read().decode('utf-8')
                
                for line in content.splitlines():
                    cleaned_line = line.strip()
                    # Skip empty lines and skip extra M3U headers so the file doesn't corrupt
                    if cleaned_line == "" or cleaned_line.startswith("#EXTM3U"):
                        continue
                    
                    combined_lines.append(cleaned_line + "\n")
                    
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            
    # Write everything directly to the final file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(combined_lines)
    
    # Count how many channels were actually saved
    channel_count = sum(1 for line in combined_lines if line.startswith("#EXTINF"))
    print(f"Done! Successfully wrote {channel_count} channels to {output_file}.")

# Run the script
build_master_list()
