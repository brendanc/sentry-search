# Sentry Event Search Tool

Tools for fetching and searching Sentry event data.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and configure your Sentry settings:
```bash
cp .env.example .env
```

3. Edit `.env` with your Sentry configuration:
```
SENTRY_TOKEN=your_token_here
SENTRY_BASE_URL=https://your-org.sentry.io
ORG=your-org-slug
PROJECT_ID=your-project-id
PROJECT_SLUG=your-project-slug
DISCOVER_QUERY=issue:YOUR-ISSUE-ID
STATS_PERIOD=10d
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

**Configuration**: All configuration is done via environment variables in your `.env` file:
- `SENTRY_BASE_URL`: Your Sentry instance URL (e.g., `https://your-org.sentry.io`)
- `ORG`: Your organization slug
- `PROJECT_ID`: Your Sentry project ID
- `PROJECT_SLUG`: Your project slug
- `DISCOVER_QUERY`: The query to search for (e.g., `issue:YOUR-ISSUE-ID`)
- `STATS_PERIOD`: Time period (e.g., `6d`, `30d`, default: `10d`)
- `MAX_EVENTS`: Safety limit for number of events to fetch (default: `500`)

### 2. Search Custom Props

Search through the saved event JSON files for Custom Prop values.

**Configuration**: You can set defaults via environment variables or command line arguments:
- `PROP_PATH`: Dot-notation path to Custom Prop (e.g., `"userInfo.userId"`)
- `VALUE_FILTER`: Optional value to filter by (set to empty to disable filtering)
- `CASE_SENSITIVE`: Whether value filtering is case sensitive (`true` or `false`)
- `OUTPUT_FORMAT`: Output format (`"table"`, `"json"`, `"csv"`, or `"values"`)

**Run with command line arguments:**
```bash
# Required: prop_path must be provided
python3 search-events.py userInfo.userId
```

**Command line options:**
```bash
# Basic search (prop_path is required)
python3 search-events.py userInfo.userName

# Filter by value
python3 search-events.py userInfo.userId --value "some-value"

# Output as JSON
python3 search-events.py userInfo.userId --format json

# Case-insensitive search
python3 search-events.py userInfo.userName --value "john" --case-insensitive

# Combine multiple options
python3 search-events.py userInfo.userName --value "john" --case-insensitive --format csv
```

**Custom Prop Path Format:**
- Use dot notation to navigate nested properties
- Paths start from `contexts["Custom props"]`
- Example: `userInfo.userId` searches `contexts["Custom props"]["userInfo"]["userId"]`

## Workflow

1. **Initial sync**: Run `sentry-search.py` to fetch events from Sentry
2. **Search**: Use `search-events.py` to find specific Custom Prop values
3. **Re-sync**: Run `sentry-search.py` again to fetch new events (existing events are cached)

## Output Formats

- `table` (default): Human-readable table format
- `json`: JSON array of results
- `csv`: CSV format for spreadsheet import
- `values`: Just the unique values (one per line)

