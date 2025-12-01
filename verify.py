import asyncio
import json
import os
from clients.rtorrent import RTorrentClient

# 1. Load the EXACT config the app uses
if os.path.exists("data/config.json"):
    with open("data/config.json", "r") as f:
        config = json.load(f)
        print(f"[INFO] Loaded data/config.json")
elif os.path.exists("config.json"):
    with open("config.json", "r") as f:
        config = json.load(f)
        print(f"[INFO] Loaded config.json")
else:
    print("[ERROR] Could not find config.json!")
    exit(1)

# 2. Extract rTorrent settings
t_type = config.get("TORRENT_CLIENT_TYPE", "unknown")
url = config.get("TORRENT_CLIENT_URL", "NOT_SET")
user = config.get("TORRENT_CLIENT_USERNAME", "NOT_SET")

print(f"--- Configuration Dump ---")
print(f"Client Type: {t_type}")
print(f"URL:         {url}")
print(f"Username:    {user}")
print(f"--------------------------")

# 3. Test the actual Client Class
async def test_client():
    if t_type != "rtorrent":
        print(f"[ERROR] Config TORRENT_CLIENT_TYPE is set to '{t_type}', but it should be 'rtorrent'!")
        return

    print("[INFO] Initializing RTorrentClient class...")
    client = RTorrentClient(config)
    
    print(f"[INFO] Attempting login to {client.url}...")
    try:
        success = await client.login()
        print(f"[SUCCESS] Login returned: {success}")
        
        status = await client.get_status()
        print(f"[SUCCESS] Get Status: {status}")
    except Exception as e:
        print(f"[FAIL] Client threw exception: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_client())
