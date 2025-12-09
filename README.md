# Sentry Event Search Tool

Tools for fetching and searching Sentry event data.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your Sentry token:
```
SENTRY_TOKEN=your_token_here
ORG=toast
```

## Usage

### 1. Sync Events from Sentry (Fetch & Save)

Run the main script to fetch events from Sentry and save them as individual JSON files:

```bash
python3 sentry-search.py
```

This will:
- Fetch events matching your configured Discover query
- Save each event to `sentry_events/{event_id}.json`
- Skip events that have already been fetched (caching)

**Configuration**: Edit the config section at the top of `sentry-search.py`:
- `PROJECT_ID`: Your Sentry project ID
- `PROJECT_SLUG`: Your project slug
- `DISCOVER_QUERY`: The query to search for (e.g., `issue:ADS-PLATFORM-SPA-J7`)
- `STATS_PERIOD`: Time period (e.g., `6d`, `30d`)
- `MAX_EVENTS`: Safety limit for number of events to fetch

### 2. Search Custom Props

Search through the saved event JSON files for Custom Prop values.

**Configuration**: Edit the config section at the top of `search-events.py`:
- `PROP_PATH`: Dot-notation path to Custom Prop (e.g., `"restaurantInfo.restaurantSetGuid"`)
- `VALUE_FILTER`: Optional value to filter by (set to `None` to disable filtering)
- `CASE_SENSITIVE`: Whether value filtering is case sensitive
- `OUTPUT_FORMAT`: Output format (`"table"`, `"json"`, `"csv"`, or `"values"`)

**Run with config values:**
```bash
# Uses values from config section
python3 search-events.py
```

**Override config via command line:**
```bash
# Override prop path
python3 search-events.py restaurantInfo.restaurantName

# Override value filter
python3 search-events.py --value "some-value"

# Override output format
python3 search-events.py --format json

# Case-insensitive search
python3 search-events.py --case-insensitive

# Combine multiple overrides
python3 search-events.py restaurantInfo.restaurantName --value "jack" --case-insensitive --format csv
```

**Custom Prop Path Format:**
- Use dot notation to navigate nested properties
- Paths start from `contexts["Custom props"]`
- Example: `restaurantInfo.restaurantSetGuid` searches `contexts["Custom props"]["restaurantInfo"]["restaurantSetGuid"]`

## Workflow

1. **Initial sync**: Run `sentry-search.py` to fetch events from Sentry
2. **Search**: Use `search-events.py` to find specific Custom Prop values
3. **Re-sync**: Run `sentry-search.py` again to fetch new events (existing events are cached)

## Output Formats

- `table` (default): Human-readable table format
- `json`: JSON array of results
- `csv`: CSV format for spreadsheet import
- `values`: Just the unique values (one per line)

