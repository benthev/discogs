# Discogs Vinyl-Only Finder

A Python tool that filters Discogs seller listings to find vinyl releases that have **no digital versions** (no WAV, MP3, CD, FLAC, etc.) available.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python vinyl_only_finder.py "<discogs_seller_url>"
```

### Example

```bash
python vinyl_only_finder.py "https://www.discogs.com/seller/woodstockmusicshop/profile?format=Vinyl&genre=Electronic"
```

## How It Works

1. Parses the seller URL to extract username and filters
2. Fetches the seller's inventory using the Discogs API
3. For each vinyl listing, checks all versions of that release
4. Filters out releases that have any digital format versions (CD, MP3, WAV, FLAC, etc.)
5. Returns only true vinyl-only releases

## Output

The script outputs:
- Progress information to stderr
- Final list of vinyl-only releases to stdout with:
  - Title
  - Artist
  - Price
  - Condition
  - Discogs URL

## API Rate Limiting

The script includes built-in delays to respect Discogs API rate limits (60 requests per minute for unauthenticated requests).

## Optional: Authentication

For higher rate limits (60 requests per minute authenticated), you can add authentication:

1. Get a Discogs API token from https://www.discogs.com/settings/developers
2. Modify the script to add the token to headers:

```python
self.headers = {
    "User-Agent": user_agent,
    "Authorization": f"Discogs token=YOUR_TOKEN_HERE"
}
```
