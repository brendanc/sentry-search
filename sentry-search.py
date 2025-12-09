#!/usr/bin/env python3
import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================
# CONFIG – Set via environment variables or .env file
# ============================================

BASE_URL = os.getenv("SENTRY_BASE_URL")
if not BASE_URL:
    raise ValueError("SENTRY_BASE_URL not found in environment variables. Please check your .env file.")

ORG_SLUG = os.getenv("ORG")
if not ORG_SLUG:
    raise ValueError("ORG not found in environment variables. Please check your .env file.")

AUTH_TOKEN = os.getenv("SENTRY_TOKEN")
if not AUTH_TOKEN:
    raise ValueError("SENTRY_TOKEN not found in environment variables. Please check your .env file.")

PROJECT_ID = os.getenv("PROJECT_ID")
if not PROJECT_ID:
    raise ValueError("PROJECT_ID not found in environment variables. Please check your .env file.")

PROJECT_SLUG = os.getenv("PROJECT_SLUG")
if not PROJECT_SLUG:
    raise ValueError("PROJECT_SLUG not found in environment variables. Please check your .env file.")

DISCOVER_QUERY = os.getenv("DISCOVER_QUERY")
if not DISCOVER_QUERY:
    raise ValueError("DISCOVER_QUERY not found in environment variables. Please check your .env file.")

STATS_PERIOD = os.getenv("STATS_PERIOD", "10d")  # Default to 10d if not specified

# Fields to retrieve from the API (required - Sentry needs to know which columns to return)
# Common fields: id, timestamp, message, title, project, release, environment, user, tags, contexts, sdk, level, type
FIELDS = [
    "id",
    "timestamp",
    "message",
    "title",
    "project",
    "release",
    "environment",
    "user",
    "tags",
    "contexts",
    "sdk",
    "level",
    "type",
]

# Safety cap so we don't accidentally slurp thousands
MAX_EVENTS = int(os.getenv("MAX_EVENTS", "500"))

# Output directory for individual event files
EVENTS_DIR = Path("sentry_events")

# ============================================
# HTTP setup
# ============================================

session = requests.Session()
session.headers.update({
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
})


def list_events_for_discover_query():
    """
    Use the organization events API to fetch all events that match
    the given Discover query, project, and statsPeriod.
    This should mirror what you're seeing in Discover.
    """
    url = f"{BASE_URL}/api/0/organizations/{ORG_SLUG}/events/"
    events = []
    cursor = None

    while True:
        params = {
            "project": PROJECT_ID,
            "query": DISCOVER_QUERY,
            "per_page": 100,
            "statsPeriod": STATS_PERIOD,
            "field": FIELDS,  # Required: specify which columns to return
        }
        if cursor:
            params["cursor"] = cursor

        print(f"Requesting page with cursor={cursor!r} ...")
        resp = session.get(url, params=params)
        if not resp.ok:
            raise RuntimeError(f"Error listing events: {resp.status_code} {resp.text}")

        response_data = resp.json()
        # Sentry API may return data in different formats:
        # - Direct list: [...events...]
        # - Object with data key: {"data": [...events...]}
        if isinstance(response_data, dict) and "data" in response_data:
            batch = response_data["data"]
        else:
            batch = response_data
        
        if not batch:
            print("No more events returned in this batch.")
            break

        events.extend(batch)
        print(f"Fetched {len(batch)} events, total so far: {len(events)}")

        # Stop if we hit our max safety limit
        if len(events) >= MAX_EVENTS:
            print(f"Reached MAX_EVENTS={MAX_EVENTS}, stopping pagination.")
            break

        # Parse pagination cursor from Link header
        link = resp.headers.get("Link", "")
        next_cursor = None
        # Example Link header (wrapped):
        # <https://...&cursor=xyz:0:0>; rel="previous"; results="false"; cursor="xyz:0:0",
        # <https://...&cursor=abc:0:1>; rel="next"; results="true"; cursor="abc:0:1"
        for part in link.split(","):
            part = part.strip()
            if 'rel="next"' in part and 'results="true"' in part:
                for seg in part.split(";"):
                    seg = seg.strip()
                    if seg.startswith("cursor="):
                        next_cursor = seg.split("=", 1)[1].strip().strip('"')
                        break

        if not next_cursor:
            print("No next cursor found, pagination finished.")
            break

        cursor = next_cursor
        time.sleep(0.1)  # be nice to the API

    return events


def fetch_full_event_details(event_id, project_slug):
    """
    Fetch full event details including all custom context data.
    Uses the individual event endpoint which returns complete event data.
    """
    url = f"{BASE_URL}/api/0/projects/{ORG_SLUG}/{project_slug}/events/{event_id}/"
    
    resp = session.get(url)
    if not resp.ok:
        # If event fetch fails, return None (event might have been deleted)
        print(f"  Warning: Failed to fetch event {event_id}: {resp.status_code}")
        return None
    
    return resp.json()


def get_event_file_path(event_id):
    """Get the file path for a given event ID."""
    return EVENTS_DIR / f"{event_id}.json"


def enrich_events_with_full_details(event_summaries):
    """
    Take event summaries from the list endpoint and fetch full details for each.
    This includes all custom context data, breadcrumbs, stack traces, etc.
    Only fetches events that haven't been saved already.
    """
    # Ensure events directory exists
    EVENTS_DIR.mkdir(exist_ok=True)
    
    enriched_events = []
    total = len(event_summaries)
    fetched_count = 0
    skipped_count = 0
    
    print(f"\nProcessing {total} events (this may take a while)...")
    
    for idx, event_summary in enumerate(event_summaries, 1):
        event_id = event_summary.get("id")
        project_slug = event_summary.get("project.name") or PROJECT_SLUG
        
        if not event_id:
            print(f"  Skipping event {idx}/{total}: no ID found")
            continue
        
        event_file_path = get_event_file_path(event_id)
        
        # Check if event file already exists
        if event_file_path.exists():
            print(f"  Loading cached event {idx}/{total}: {event_id}")
            try:
                with event_file_path.open("r", encoding="utf-8") as f:
                    cached_event = json.load(f)
                enriched_events.append(cached_event)
                skipped_count += 1
                continue
            except (json.JSONDecodeError, IOError) as e:
                print(f"  Warning: Failed to load cached event {event_id}: {e}. Will re-fetch.")
        
        # Fetch event from API
        print(f"  Fetching event {idx}/{total}: {event_id}")
        full_event = fetch_full_event_details(event_id, project_slug)
        
        if full_event:
            # Merge summary data with full event data (full event takes precedence)
            enriched_event = {**event_summary, **full_event}
            
            # Save event to its own JSON file
            try:
                with event_file_path.open("w", encoding="utf-8") as f:
                    json.dump(enriched_event, f, indent=2, sort_keys=True)
                print(f"    Saved to {event_file_path}")
            except IOError as e:
                print(f"    Warning: Failed to save event {event_id}: {e}")
            
            enriched_events.append(enriched_event)
            fetched_count += 1
        else:
            # If full fetch failed, keep the summary and save it
            try:
                with event_file_path.open("w", encoding="utf-8") as f:
                    json.dump(event_summary, f, indent=2, sort_keys=True)
            except IOError as e:
                print(f"    Warning: Failed to save event summary {event_id}: {e}")
            enriched_events.append(event_summary)
        
        # Be nice to the API - small delay between requests
        time.sleep(0.2)
    
    print(f"\nSummary: Fetched {fetched_count} new events, loaded {skipped_count} from cache")
    return enriched_events


def main():
    print(f"Fetching events for org={ORG_SLUG}, project_id={PROJECT_ID}, query={DISCOVER_QUERY!r}, statsPeriod={STATS_PERIOD!r}")
    event_summaries = list_events_for_discover_query()

    print(f"\nTotal event summaries fetched: {len(event_summaries)}")
    if not event_summaries:
        print("No events found. Double-check ORG_SLUG, AUTH_TOKEN, and DISCOVER_QUERY.")
        return

    # Fetch full event details including all custom context data
    # Events are automatically saved to individual JSON files
    events = enrich_events_with_full_details(event_summaries)

    print(f"\nProcessed {len(events)} events. Individual event files saved to: {EVENTS_DIR.resolve()}")


if __name__ == "__main__":
    main()
