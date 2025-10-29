#!/usr/bin/env python3
"""
Quick test script to demonstrate the organize endpoints.
This will test with the actual hash found in metadata.json
"""

import asyncio
import json
from pathlib import Path
import httpx

async def quick_test():
    print("🧪 Quick Organize Route Test")
    print("=" * 40)
    
    # Read metadata to get a real hash
    metadata_path = Path("../data/metadata.json")
    if metadata_path.exists():
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        if metadata:
            # Get the first hash
            sample_hash = list(metadata.keys())[0]
            sample_meta = metadata[sample_hash]
            print(f"📚 Found torrent: '{sample_meta['title']}' by {sample_meta['author']}")
            print(f"🔍 Hash: {sample_hash}")
            print(f"📊 Organized: {sample_meta.get('organized', False)}")
            print()
        else:
            sample_hash = "dummy_hash_for_testing"
            print("📝 No torrents in metadata, using dummy hash")
    else:
        sample_hash = "dummy_hash_for_testing"
        print("📝 No metadata file found, using dummy hash")
    
    # Test against localhost:5000
    base_url = "http://localhost:5000"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        print(f"🔍 Testing server at {base_url}")
        
        try:
            # Test server connectivity
            response = await client.get(f"{base_url}/")
            print(f"✅ Server is running (status: {response.status_code})")
        except Exception as e:
            print(f"❌ Server not accessible: {e}")
            print("💡 Make sure your app is running on localhost:5000")
            return
        
        print()
        
        # Test single hash organization
        print(f"🎯 Testing single torrent organization...")
        try:
            response = await client.post(f"{base_url}/organize/{sample_hash}")
            print(f"📡 Status: {response.status_code}")
            if response.headers.get('content-type', '').startswith('application/json'):
                data = response.json()
                print(f"📄 Response: {json.dumps(data, indent=2)}")
            else:
                print(f"📄 Response: {response.text}")
        except Exception as e:
            print(f"❌ Single organize test failed: {e}")
        
        print()
        
        # Test batch organization
        print(f"🎯 Testing batch organization...")
        try:
            response = await client.post(f"{base_url}/organize")
            print(f"📡 Status: {response.status_code}")
            if response.headers.get('content-type', '').startswith('application/json'):
                data = response.json()
                print(f"📄 Response: {json.dumps(data, indent=2)}")
            else:
                print(f"📄 Response: {response.text}")
        except Exception as e:
            print(f"❌ Batch organize test failed: {e}")
    
    print("\n🏁 Test completed!")

if __name__ == "__main__":
    asyncio.run(quick_test())