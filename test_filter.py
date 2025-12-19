#!/usr/bin/env python3
"""
Test script to inspect the first few listings and see their genre/format details
"""

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

def test_listings(seller_username, num_entries=10):
    """Fetch and display details of first N listings"""
    
    base_url = "https://api.discogs.com"
    headers = {"User-Agent": "VinylOnlyFinder/1.0"}
    
    # Add API token if available
    api_token = os.getenv("DISCOGS_API_KEY")
    if api_token:
        headers["Authorization"] = f"Discogs token={api_token}"
        print("Using authenticated API requests\n")
    
    session = requests.Session()
    session.headers.update(headers)
    
    # Fetch first page
    url = f"{base_url}/users/{seller_username}/inventory"
    params = {"per_page": num_entries, "page": 1}
    
    print(f"Fetching first {num_entries} listings from {seller_username}...\n")
    response = session.get(url, params=params)
    
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return
    
    data = response.json()
    listings = data.get("listings", [])
    
    print(f"{'='*100}")
    print(f"Found {len(listings)} listings\n")
    
    for i, listing in enumerate(listings, 1):
        release = listing.get("release", {})
        price = listing.get("price", {})
        release_id = release.get('id')
        
        print(f"{'='*100}")
        print(f"ENTRY #{i}")
        print(f"{'='*100}")
        print(f"Title:       {release.get('description', 'Unknown')}")
        print(f"Artist:      {release.get('artist', 'Unknown')}")
        print(f"Release ID:  {release_id}")
        print(f"\nFROM INVENTORY LISTING:")
        print(f"  Format:    {release.get('format', 'Not specified')}")
        print(f"  Genres:    {release.get('genres', [])}")
        
        # Fetch full release details
        print(f"\nFetching release details...")
        release_response = session.get(f"{base_url}/releases/{release_id}")
        if release_response.status_code == 200:
            release_data = release_response.json()
            print(f"\nFROM RELEASE PAGE:")
            print(f"  Genres:    {release_data.get('genres', [])}")
            print(f"  Styles:    {release_data.get('styles', [])}")
            print(f"  Formats:   {release_data.get('formats', [])}")
            
            master_id = release_data.get('master_id')
            if master_id:
                print(f"\n  Master ID: {master_id}")
                print(f"  Fetching master release details...")
                import time
                time.sleep(0.5)
                master_response = session.get(f"{base_url}/masters/{master_id}")
                if master_response.status_code == 200:
                    master_data = master_response.json()
                    print(f"\nFROM MASTER RELEASE PAGE:")
                    print(f"  Genres:    {master_data.get('genres', [])}")
                    print(f"  Styles:    {master_data.get('styles', [])}")
                else:
                    print(f"  Error fetching master: {master_response.status_code}")
            else:
                print(f"\n  No master release")
        else:
            print(f"  Error fetching release: {release_response.status_code}")
        
        print(f"\nPrice:       {price.get('value', 0)} {price.get('currency', '')}")
        print(f"Condition:   {listing.get('condition', 'Unknown')}")
        print(f"URL:         https://www.discogs.com/release/{release_id}")
        print()
        
        import time
        time.sleep(1)  # Rate limiting


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_filter.py <seller_username> [num_entries]")
        print("\nExample:")
        print("  python test_filter.py woodstockmusicshop 10")
        sys.exit(1)
    
    seller = sys.argv[1]
    num = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    test_listings(seller, num)
