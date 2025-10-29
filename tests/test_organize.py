#!/usr/bin/env python3
"""
Test script for the /organize endpoints in the MyAnonamouse Search app.

This script tests both:
- /organize (batch organization)
- /organize/<hash_val> (single torrent organization)

Usage:
    python test_organize.py --host localhost --port 5000
    python test_organize.py --single-hash abc123def456  # Test specific hash
    python test_organize.py --batch  # Test batch organization
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
import httpx
from datetime import datetime


class OrganizeTestClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        await self.client.aclose()
    
    async def test_single_organize(self, hash_val: str):
        """Test organizing a single torrent by hash."""
        print(f"🧪 Testing single torrent organization for hash: {hash_val}")
        
        url = f"{self.base_url}/organize/{hash_val}"
        try:
            response = await self.client.post(url)
            
            print(f"📡 Response Status: {response.status_code}")
            print(f"📋 Response Headers: {dict(response.headers)}")
            
            if response.headers.get('content-type', '').startswith('application/json'):
                data = response.json()
                print(f"📄 Response JSON:")
                print(json.dumps(data, indent=2))
            else:
                print(f"📄 Response Text: {response.text}")
            
            return response.status_code, response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            
        except httpx.RequestError as e:
            print(f"❌ Request failed: {e}")
            return None, str(e)
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return None, str(e)
    
    async def test_batch_organize(self):
        """Test batch organization of all unorganized torrents."""
        print("🧪 Testing batch torrent organization")
        
        url = f"{self.base_url}/organize"
        try:
            response = await self.client.post(url)
            
            print(f"📡 Response Status: {response.status_code}")
            print(f"📋 Response Headers: {dict(response.headers)}")
            
            if response.headers.get('content-type', '').startswith('application/json'):
                data = response.json()
                print(f"📄 Response JSON:")
                print(json.dumps(data, indent=2))
                
                # If it's a batch response, show summary
                if 'results' in data:
                    results = data['results']
                    print(f"\n📊 Batch Summary:")
                    print(f"   Total: {results['total']}")
                    print(f"   Succeeded: {results['succeeded']}")
                    print(f"   Failed: {results['failed']}")
                    print(f"   Skipped: {results['skipped']}")
                    
                    if results['details']:
                        print(f"\n📝 Details:")
                        for detail in results['details'][:5]:  # Show first 5 details
                            status = "✅" if detail['success'] else "❌"
                            print(f"   {status} {detail['hash'][:8]}... - {detail['message'][:80]}...")
                        
                        if len(results['details']) > 5:
                            print(f"   ... and {len(results['details']) - 5} more")
            else:
                print(f"📄 Response Text: {response.text}")
            
            return response.status_code, response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            
        except httpx.RequestError as e:
            print(f"❌ Request failed: {e}")
            return None, str(e)
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return None, str(e)
    
    async def check_server_status(self):
        """Check if the server is running and accessible."""
        print(f"🔍 Checking server status at {self.base_url}")
        
        try:
            response = await self.client.get(f"{self.base_url}/")
            print(f"✅ Server is accessible (Status: {response.status_code})")
            return True
        except httpx.RequestError as e:
            print(f"❌ Server not accessible: {e}")
            return False
    
    async def get_metadata_info(self):
        """Try to get information about the metadata file (if accessible)."""
        print("📊 Checking for metadata information...")
        
        # This assumes the data directory is accessible - adjust path as needed
        metadata_path = Path("../data/metadata.json")
        
        if metadata_path.exists():
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                total_torrents = len(metadata)
                organized_count = sum(1 for m in metadata.values() if m.get('organized', False))
                unorganized_count = total_torrents - organized_count
                
                print(f"📈 Metadata Stats:")
                print(f"   Total torrents: {total_torrents}")
                print(f"   Organized: {organized_count}")
                print(f"   Unorganized: {unorganized_count}")
                
                if unorganized_count > 0:
                    print(f"🔍 Sample unorganized hashes:")
                    unorganized_hashes = [h for h, m in metadata.items() if not m.get('organized', False)]
                    for hash_val in unorganized_hashes[:3]:
                        meta = metadata[hash_val]
                        print(f"   {hash_val} - '{meta.get('title', 'Unknown')}' by {meta.get('author', 'Unknown')}")
                
                return unorganized_count > 0, unorganized_hashes[:1] if unorganized_count > 0 else []
                
            except Exception as e:
                print(f"⚠️ Could not read metadata file: {e}")
                return False, []
        else:
            print("⚠️ Metadata file not found at ./data/metadata.json")
            return False, []


async def main():
    parser = argparse.ArgumentParser(description="Test the organize endpoints")
    parser.add_argument("--host", default="localhost", help="Server host (default: localhost)")
    parser.add_argument("--port", default=5000, type=int, help="Server port (default: 5000)")
    parser.add_argument("--single-hash", help="Test organizing a specific hash")
    parser.add_argument("--batch", action="store_true", help="Test batch organization")
    parser.add_argument("--auto", action="store_true", help="Auto-detect and test based on metadata")
    
    args = parser.parse_args()
    
    base_url = f"http://{args.host}:{args.port}"
    client = OrganizeTestClient(base_url)
    
    try:
        print(f"🚀 MyAnonamouse Search - Organize Route Tester")
        print(f"🎯 Target: {base_url}")
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Check server status first
        if not await client.check_server_status():
            print("❌ Cannot proceed - server is not accessible")
            return 1
        
        print()
        
        # If specific hash provided, test that
        if args.single_hash:
            status_code, response = await client.test_single_organize(args.single_hash)
            if status_code:
                print(f"\n✅ Single hash test completed with status {status_code}")
            else:
                print(f"\n❌ Single hash test failed: {response}")
        
        # If batch requested, test that
        elif args.batch:
            status_code, response = await client.test_batch_organize()
            if status_code:
                print(f"\n✅ Batch test completed with status {status_code}")
            else:
                print(f"\n❌ Batch test failed: {response}")
        
        # Auto mode - check metadata and decide what to test
        elif args.auto:
            has_unorganized, sample_hashes = await client.get_metadata_info()
            print()
            
            if has_unorganized and sample_hashes:
                print(f"🎯 Found unorganized torrents, testing single hash: {sample_hashes[0]}")
                status_code, response = await client.test_single_organize(sample_hashes[0])
                if status_code:
                    print(f"\n✅ Auto single hash test completed with status {status_code}")
                
                print(f"\n🎯 Now testing batch organization...")
                status_code, response = await client.test_batch_organize()
                if status_code:
                    print(f"\n✅ Auto batch test completed with status {status_code}")
            else:
                print("🎯 No unorganized torrents found, testing batch endpoint anyway...")
                status_code, response = await client.test_batch_organize()
                if status_code:
                    print(f"\n✅ Batch test completed with status {status_code}")
        
        # Default - test both endpoints with dummy data
        else:
            print("🎯 No specific test requested, running default tests...")
            
            # Test with a dummy hash first
            dummy_hash = "1234567890abcdef1234567890abcdef12345678"
            print(f"\n1️⃣ Testing single organize with dummy hash: {dummy_hash}")
            status_code, response = await client.test_single_organize(dummy_hash)
            if status_code:
                print(f"✅ Dummy hash test completed with status {status_code}")
            
            # Test batch organization
            print(f"\n2️⃣ Testing batch organization")
            status_code, response = await client.test_batch_organize()
            if status_code:
                print(f"✅ Batch test completed with status {status_code}")
            
            # Check metadata for real hashes to test
            print(f"\n3️⃣ Checking for real torrents to test...")
            has_unorganized, sample_hashes = await client.get_metadata_info()
            if sample_hashes:
                print(f"🎯 Testing with real hash: {sample_hashes[0]}")
                status_code, response = await client.test_single_organize(sample_hashes[0])
                if status_code:
                    print(f"✅ Real hash test completed with status {status_code}")
        
        print("\n" + "=" * 60)
        print(f"🏁 Testing completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return 0
        
    except KeyboardInterrupt:
        print("\n⚠️ Testing interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error during testing: {e}")
        return 1
    finally:
        await client.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)