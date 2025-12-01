# debug_rtorrent.py
import asyncio
import httpx

# MATCH THESE TO YOUR CURL COMMAND
URL = "http://localhost:8096/RPC2"
USERNAME = "" 
PASSWORD = ""

async def test_connection():
    payload = """<?xml version='1.0'?>
<methodCall>
<methodName>system.client_version</methodName>
<params></params>
</methodCall>"""
    
    headers = {"Content-Type": "text/xml"}
    auth = (USERNAME, PASSWORD) if USERNAME else None
    
    print(f"Connecting to {URL}...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(URL, content=payload, headers=headers, auth=auth)
            print(f"Status Code: {resp.status_code}")
            print(f"Response Body: {resp.text[:100]}...")
    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
