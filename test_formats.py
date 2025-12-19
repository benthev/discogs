#!/usr/bin/env python3
"""
Test script to display all formats for all versions of a given release.
Usage: python test_formats.py <release_id>
"""

import os
import sys
import time
import json
import requests
from dotenv import load_dotenv

load_dotenv()


def get_release_info(release_id):
    """Get release info including master_id."""
    headers = {"User-Agent": "FormatChecker/1.0"}
    api_token = os.getenv("DISCOGS_API_KEY")
    if api_token:
        headers["Authorization"] = f"Discogs token={api_token}"
    
    time.sleep(1)
    response = requests.get(
        f"https://api.discogs.com/releases/{release_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching release: {response.status_code}")
        return None


def get_all_versions(master_id):
    """Get all versions of a master release."""
    headers = {"User-Agent": "FormatChecker/1.0"}
    api_token = os.getenv("DISCOGS_API_KEY")
    if api_token:
        headers["Authorization"] = f"Discogs token={api_token}"
    
    all_versions = []
    page = 1
    
    while True:
        time.sleep(1)
        response = requests.get(
            f"https://api.discogs.com/masters/{master_id}/versions",
            params={"per_page": 100, "page": page},
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"Error fetching versions: {response.status_code}")
            break
        
        data = response.json()
        versions = data.get("versions", [])
        
        if not versions:
            break
        
        all_versions.extend(versions)
        
        pagination = data.get("pagination", {})
        if page >= pagination.get("pages", 0):
            break
        
        page += 1
    
    return all_versions


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_formats.py <release_id>")
        print("\nExample:")
        print("  python test_formats.py 2034353")
        sys.exit(1)
    
    release_id = sys.argv[1]
    
    print(f"Fetching release {release_id}...")
    release_info = get_release_info(release_id)
    
    if not release_info:
        sys.exit(1)
    
    print(f"\nRelease: {release_info.get('title')}")
    print(f"Artist: {release_info.get('artists', [{}])[0].get('name', 'Unknown')}")
    
    master_id = release_info.get("master_id")
    if not master_id:
        print("\nNo master release ID found. This release has no other versions.")
        sys.exit(0)
    
    print(f"Master ID: {master_id}")
    print(f"\nFetching all versions...")
    
    versions = get_all_versions(master_id)
    print(f"Found {len(versions)} versions\n")
    print("=" * 80)
    
    # Show raw JSON for all versions
    print("\nRAW JSON FOR ALL VERSIONS:")
    print("-" * 80)
    for i, version in enumerate(versions, 1):
        print(f"\n[Version {i}]")
        print(json.dumps(version, indent=2))
        print("-" * 80)
    
    # Group by format
    format_groups = {}
    
    for version in versions:
        format_str = version.get("format", "Unknown")
        title = version.get("title", "Unknown")
        country = version.get("country", "Unknown")
        label = version.get("label", "Unknown")
        catno = version.get("catno", "")
        version_id = version.get("id", "")
        
        if format_str not in format_groups:
            format_groups[format_str] = []
        
        format_groups[format_str].append({
            "title": title,
            "country": country,
            "label": label,
            "catno": catno,
            "id": version_id
        })
    
    # Print all versions with full details
    print("\nALL VERSIONS (with format details):")
    print("-" * 80)
    for i, version in enumerate(versions, 1):
        format_str = version.get("format", "Unknown")
        title = version.get("title", "Unknown")
        country = version.get("country", "Unknown")
        label = version.get("label", "Unknown")
        catno = version.get("catno", "")
        version_id = version.get("id", "")
        year = version.get("year", "Unknown")
        
        print(f"\n[{i}] {title}")
        print(f"    Format: {format_str}")
        print(f"    Country: {country} | Year: {year}")
        print(f"    Label: {label} ({catno})")
        print(f"    ID: {version_id}")
        print(f"    URL: https://www.discogs.com/release/{version_id}")
    
    # Print grouped summary
    print("\n" + "=" * 80)
    print("\nFORMAT SUMMARY:")
    print("-" * 80)
    for format_name in sorted(format_groups.keys()):
        count = len(format_groups[format_name])
        print(f"{format_name}: {count} versions")
    
    # Check for non-vinyl/non-cassette formats using major_formats
    print("\n" + "=" * 80)
    print("FORMAT CHECK (using major_formats field):")
    print("-" * 80)
    
    allowed_formats = ["vinyl", "cassette"]
    has_non_vinyl = False
    non_vinyl_versions = []
    
    for version in versions:
        major_formats = version.get("major_formats", [])
        non_allowed = [fmt for fmt in major_formats if fmt.lower() not in allowed_formats]
        
        if non_allowed:
            has_non_vinyl = True
            non_vinyl_versions.append((version.get("title"), non_allowed))
    
    if non_vinyl_versions:
        print(f"✗ Found {len(non_vinyl_versions)} versions with non-vinyl/non-cassette formats:\n")
        for title, formats in non_vinyl_versions[:10]:  # Show first 10
            print(f"  - {title}: {', '.join(formats)}")
        if len(non_vinyl_versions) > 10:
            print(f"  ... and {len(non_vinyl_versions) - 10} more")
        print(f"\n✗ This release HAS non-vinyl/non-cassette versions")
    else:
        print("✓ No non-vinyl/non-cassette formats found - this is VINYL/CASSETTE-ONLY")
    
    # Summary
    vinyl_cassette_count = len(versions) - len(non_vinyl_versions)
    print(f"\nTotal versions: {len(versions)}")
    print(f"Vinyl/Cassette only: {vinyl_cassette_count}")
    print(f"Has other formats: {len(non_vinyl_versions)}")


if __name__ == "__main__":
    main()
