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
        self.min_request_delay = 1.0  # Minimum delay between requests in seconds
        self.last_request_time = 0

    def _rate_limit(self, delay=None):
        """Enforce rate limiting between API requests."""
        if delay is None:
            delay = self.min_request_delay

        elapsed = time.time() - self.last_request_time
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self.last_request_time = time.time()

    def _make_request(self, url, params=None, max_retries=5):
        """Make an API request with rate limiting and exponential backoff."""
        for attempt in range(max_retries):
            self._rate_limit()
            response = self.session.get(url, params=params)

            if response.status_code == 200:
                return response
            elif response.status_code == 429:
                # Rate limited - exponential backoff
                wait_time = (2 ** attempt) * 2  # 2, 4, 8, 16, 32 seconds
                print(
                    f"Rate limited. Waiting {wait_time}s before retry {attempt + 1}/{max_retries}...", file=sys.stderr)
                time.sleep(wait_time)
            else:
                return response

        return response

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

    def get_seller_inventory(self, username):
        """Generator that yields inventory items page by page."""
        url = f"{self.base_url}/users/{username}/inventory"
        params = {"per_page": 100, "page": 1}  # API max is 100

        while True:
            print(f"Fetching page {params['page']}...", file=sys.stderr)
            response = self._make_request(url, params=params)

            if response.status_code != 200:
                print(
                    f"Error: {response.status_code} - {response.text}", file=sys.stderr)
                break

            data = response.json()
            listings = data.get("listings", [])
            pagination = data.get("pagination", {})

            if not listings:
                break

            # Yield all listings
            for listing in listings:
                yield listing

            print(
                f"  -> Page {params['page']}: {len(listings)} listings fetched", file=sys.stderr)

            # Check if there are more pages
            current_page = pagination.get("page", params["page"])
            total_pages = pagination.get("pages", 0)

            if current_page >= total_pages:
                break

            params["page"] += 1

    def get_release_info(self, release_id):
        """Get release details including master_id and genres."""
        response = self._make_request(f"{self.base_url}/releases/{release_id}")
        if response.status_code == 200:
            return response.json()
        return None

    def get_master_info(self, master_id):
        """Get master release info including genres."""
        response = self._make_request(f"{self.base_url}/masters/{master_id}")
        if response.status_code == 200:
            return response.json()
        return None

    def get_release_versions(self, master_id):
        """Get all versions of a master release to check for digital formats."""
        url = f"{self.base_url}/masters/{master_id}/versions"
        params = {"per_page": 500, "page": 1}

        all_versions = []
        while True:
            response = self._make_request(url, params=params)

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

        return all_versions

    def has_non_vinyl_version(self, versions):
        """Check if any version has a non-vinyl/non-cassette major format."""
        allowed_formats = ["vinyl", "cassette"]

        for version in versions:
            # Check major_formats field which contains format names like "Vinyl", "CD", etc.
            major_formats = version.get("major_formats", [])

            # If there are any major formats other than Vinyl or Cassette, it's not vinyl-only
            for fmt in major_formats:
                if fmt.lower() not in allowed_formats:
                    return True

        return False

    def filter_vinyl_only(self, url, genre_filter="Electronic"):
        """Main function to filter vinyl-only releases."""
        username, params = self.parse_seller_url(url)

        # Get genre filter from URL if explicitly provided, else use default
        url_genre = params.get("genre", [None])[0]
        if url_genre:
            genre_filter = url_genre

        print(f"Fetching inventory for seller: {username}", file=sys.stderr)
        if genre_filter:
            print(f"Genre filter: {genre_filter}", file=sys.stderr)
        print(f"Format filter: Vinyl only", file=sys.stderr)
        print()

        listing_count = 0
        vinyl_only_count = 0
        checked_count = 0

        print("\nScanning inventory...\n", file=sys.stderr)

        for listing in self.get_seller_inventory(username):
            listing_count += 1
            release = listing.get("release", {})
            release_id = release.get("id")
            title = release.get("description", "Unknown")
            artist = release.get("artist", "Unknown")
            price = listing.get("price", {})

            # Get full release details
            release_info = self.get_release_info(release_id)
            if not release_info:
                continue

            # Filter by format - must have Vinyl
            formats = release_info.get("formats", [])
            has_vinyl = any(fmt.get("name", "").lower()
                            == "vinyl" for fmt in formats)
            if not has_vinyl:
                continue

            master_id = release_info.get("master_id")

            # Filter by genre using master release data
            if genre_filter:
                if master_id:
                    master_info = self.get_master_info(master_id)
                    if master_info:
                        genres = [g.lower()
                                  for g in master_info.get("genres", [])]
                    else:
                        genres = [g.lower()
                                  for g in release_info.get("genres", [])]
                else:
                    genres = [g.lower()
                              for g in release_info.get("genres", [])]

                if genre_filter.lower() not in genres:
                    continue

            checked_count += 1

            # Check for digital versions if there's a master release
            is_vinyl_only = False
            if not master_id:
                is_vinyl_only = True
                status = "✓ VINYL-ONLY (no master release)"
                genres_str = ", ".join(release_info.get("genres", []))
            else:
                versions = self.get_release_versions(master_id)

                if not self.has_non_vinyl_version(versions):
                    is_vinyl_only = True
                    status = f"✓ VINYL-ONLY ({len(versions)} versions, vinyl/cassette only)"
                else:
                    status = f"✗ has non-vinyl ({len(versions)} versions)"

                # Get genres from master
                master_info = self.get_master_info(master_id)
                genres_str = ", ".join(master_info.get(
                    "genres", [])) if master_info else "Unknown"

            # Print one-line summary
            price_str = f"{price.get('value', '')} {price.get('currency', '')}".strip(
            )
            print(f"[{checked_count}] {status} | {genres_str} | {artist} - {title} | ${price_str} | https://www.discogs.com/release/{release_id}")

            if is_vinyl_only:
                vinyl_only_count += 1

        print(f"\n{'='*80}")
        print(
            f"Total: {listing_count} fetched, {checked_count} matched genre filter, {vinyl_only_count} vinyl-only\n")


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python vinyl_only_finder.py <discogs_seller_url> [genre]")
        print("\nExamples:")
        print("  python vinyl_only_finder.py 'https://www.discogs.com/seller/woodstockmusicshop/profile'")
        print("  python vinyl_only_finder.py 'https://www.discogs.com/seller/woodstockmusicshop/profile' Rock")
        print("  python vinyl_only_finder.py 'https://www.discogs.com/seller/woodstockmusicshop/profile' ''  # No genre filter")
        print("\nDefault genre filter: Electronic")
        sys.exit(1)

    url = sys.argv[1]
    genre = sys.argv[2] if len(sys.argv) > 2 else "Electronic"

    # Empty string means no filter
    if genre == "":
        genre = None

    finder = DiscogsVinylFinder()
    finder.filter_vinyl_only(url, genre_filter=genre)


if __name__ == "__main__":
    main()
