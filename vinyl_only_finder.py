#!/usr/bin/env python3
"""
Discogs Vinyl-Only Finder

Takes a Discogs seller URL and returns vinyl listings that have NO digital versions
(no WAV, MP3, CD, etc.) under any other versions of the release.
"""

import os
import re
import sys
import time
import requests
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DiscogsVinylFinder:
    def __init__(self, user_agent="VinylOnlyFinder/1.0"):
        self.base_url = "https://api.discogs.com"
        self.headers = {"User-Agent": user_agent}
        
        # Add API token if available
        api_token = os.getenv("DISCOGS_API_KEY")
        if api_token:
            self.headers["Authorization"] = f"Discogs token={api_token}"
            print("Using authenticated API requests", file=sys.stderr)
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def parse_seller_url(self, url):
        """Extract seller username and filters from URL."""
        # Example: https://www.discogs.com/seller/woodstockmusicshop/profile?format=Vinyl&genre=Electronic
        match = re.search(r'/seller/([^/]+)/', url)
        if not match:
            raise ValueError("Invalid Discogs seller URL")
        
        username = match.group(1)
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        return username, params
    
    def get_seller_inventory(self, username, format_filter=None, genre_filter=None):
        """Generator that yields inventory items page by page."""
        url = f"{self.base_url}/users/{username}/inventory"
        params = {"per_page": 100, "page": 1}  # API max is 100
        
        # Note: Discogs inventory API doesn't support format/genre filters
        # We must filter client-side
        self.format_filter = format_filter
        self.genre_filter = genre_filter
        
        while True:
            print(f"Fetching page {params['page']}...", file=sys.stderr)
            response = self.session.get(url, params=params)
            
            if response.status_code != 200:
                print(f"Error: {response.status_code} - {response.text}", file=sys.stderr)
                break
            
            data = response.json()
            listings = data.get("listings", [])
            pagination = data.get("pagination", {})
            
            if not listings:
                break
            
            # Track filtering stats
            page_count = 0
            filtered_count = 0
            
            # Yield each listing (with client-side filtering)
            for listing in listings:
                page_count += 1
                release = listing.get("release", {})
                
                # Filter by genre if specified
                if self.genre_filter:
                    genres = [g.lower() for g in release.get("genres", [])]
                    if self.genre_filter.lower() not in genres:
                        continue
                
                # Filter by format if specified
                if self.format_filter:
                    format_str = release.get("format", "").lower()
                    if self.format_filter.lower() not in format_str:
                        continue
                
                filtered_count += 1
                yield listing
            
            print(f"  -> Page {params['page']}: {page_count} listings, {filtered_count} matched filters", file=sys.stderr)
            
            # Check if there are more pages
            current_page = pagination.get("page", params["page"])
            total_pages = pagination.get("pages", 0)
            
            if current_page >= total_pages:
                break
            
            params["page"] += 1
            time.sleep(1)  # Be respectful to the API
    
    def get_release_versions(self, master_id=None, release_id=None):
        """Get all versions of a release to check for digital formats."""
        if master_id:
            url = f"{self.base_url}/masters/{master_id}/versions"
            params = {"per_page": 500, "page": 1}  # Increased to get more versions
            
            all_versions = []
            while True:
                response = self.session.get(url, params=params)
                
                if response.status_code != 200:
                    return []
                
                data = response.json()
                versions = data.get("versions", [])
                
                if not versions:
                    break
                
                all_versions.extend(versions)
                
                pagination = data.get("pagination", {})
                current_page = pagination.get("page", params["page"])
                total_pages = pagination.get("pages", 0)
                
                if current_page >= total_pages:
                    break
                
                params["page"] += 1
                time.sleep(0.5)
            
            return all_versions
        
        elif release_id:
            # Get the release details to find the master_id
            response = self.session.get(f"{self.base_url}/releases/{release_id}")
            if response.status_code == 200:
                data = response.json()
                master_id = data.get("master_id")
                if master_id:
                    time.sleep(0.5)
                    return self.get_release_versions(master_id=master_id)
            return []
        
        return []
    
    def has_digital_version(self, versions):
        """Check if any version has a digital or CD format."""
        digital_formats = ["cd", "mp3", "wav", "flac", "aac", "file", "digital"]
        
        for version in versions:
            format_str = version.get("format", "").lower()
            if any(fmt in format_str for fmt in digital_formats):
                return True
        
        return False
    
    def filter_vinyl_only(self, url):
        """Main function to filter vinyl-only releases."""
        username, params = self.parse_seller_url(url)
        
        format_filter = params.get("format", [None])[0]
        genre_filter = params.get("genre", [None])[0]
        
        print(f"Fetching inventory for seller: {username}", file=sys.stderr)
        if format_filter:
            print(f"Format filter: {format_filter}", file=sys.stderr)
        if genre_filter:
            print(f"Genre filter: {genre_filter}", file=sys.stderr)
        print()
        
        listing_count = 0
        vinyl_only_count = 0
        
        print("\nScanning inventory...\n", file=sys.stderr)
        
        for listing in self.get_seller_inventory(username, format_filter, genre_filter):
            listing_count += 1
            release = listing.get("release", {})
            release_id = release.get("id")
            title = release.get("description", "Unknown")
            artist = release.get("artist", "Unknown")
            price = listing.get("price", {})
            
            # Get all versions of this release
            versions = self.get_release_versions(release_id=release_id)
            
            is_vinyl_only = False
            if not versions:
                is_vinyl_only = True
                status = "✓ VINYL-ONLY (no other versions)"
            elif not self.has_digital_version(versions):
                is_vinyl_only = True
                status = f"✓ VINYL-ONLY ({len(versions)} versions, all vinyl)"
            else:
                status = f"✗ HAS DIGITAL ({len(versions)} versions)"
            
            # Print one-line summary
            price_str = f"{price.get('value', '')} {price.get('currency', '')}".strip()
            print(f"[{listing_count}] {status} | {artist} - {title} | ${price_str} | https://www.discogs.com/release/{release_id}")
            
            if is_vinyl_only:
                vinyl_only_count += 1
            
            time.sleep(1)  # Rate limiting
        
        print(f"\n{'='*80}")
        print(f"Total: {listing_count} checked, {vinyl_only_count} vinyl-only\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python vinyl_only_finder.py <discogs_seller_url>")
        print("\nExample:")
        print("  python vinyl_only_finder.py 'https://www.discogs.com/seller/woodstockmusicshop/profile?format=Vinyl&genre=Electronic'")
        sys.exit(1)
    
    url = sys.argv[1]
    
    finder = DiscogsVinylFinder()
    finder.filter_vinyl_only(url)


if __name__ == "__main__":
    main()
