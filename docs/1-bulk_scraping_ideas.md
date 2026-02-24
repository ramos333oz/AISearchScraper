# YouTube Monthly Bulk Scraper Ideas (Future Ideas)

## Problem Statement

The current YouTube RSS feed scraper only provides the 15 most recent videos for a specific channel. If we want to scrape, transcribe, and summarize an entire month of videos from the same creator, relying on the RSS feed is insufficient as older videos fall off the feed.

## Proposed Solutions

### Option 1: The `scrapetube` Library (Recommended)

This approach simulates a user scrolling down a channel page to retrieve all video metadata without requiring Official YouTube Data API keys or quotas.

- **How it works:**
  1.  Create a separate script (e.g., `bulk_scrape.py`).
  2.  Use the `scrapetube` Python library to fetch all videos from the target channel ID.
  3.  Loop through the list of returned videos and parse the `published` date.
  4.  Filter for videos published within the specific target month/year.
  5.  Run each matching video ID through the existing `get_video_transcript`, `generate_summary`, and `send_telegram_message` pipeline.
- **Pros:** Requires no setup of Google Cloud API keys, easy to implement, no hard quotas.
- **Cons:** Not an official API; relies on scraping, which can technically break if YouTube heavily alters its HTML structure.

### Option 2: The Official YouTube Data API v3

This is the enterprise-grade solution utilizing Google Cloud Platform to officially query YouTube's database.

- **How it works:**
  1.  Register a project on Google Cloud Platform and enable the YouTube Data API v3.
  2.  Generate an API Key.
  3.  Use the official `google-api-python-client` to make a specific Search API request, filtering by the channel ID and restricting the `publishedAfter` and `publishedBefore` parameters to the target month.
  4.  Extract video IDs from the API response and push them through our existing summary pipeline.
- **Pros:** 100% reliable, returns exact datetimes and metadata, officially supported by YouTube.
- **Cons:** Requires Google Cloud setup and managing API keys. The API operates on a rigid quota system (e.g., free tier allows ~10,000 units/day; searches cost 100 units each).

## Implementation Recommendation

Start with **Option 1 (`scrapetube`)**. It integrates seamlessly with the current lightweight architecture and provides exactly the data needed without navigating Google Cloud quotas or complex authentication steps. The existing modular methods in `main.py` can be easily imported and reused by the new script.
