#!/usr/bin/env python3
"""
Search tool for Sentry event JSON files.

Searches through Custom Props in event JSON files using dot notation paths.
Example: search for "userInfo.userId"
"""
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# ============================================
# CONFIG – EDIT THESE (or override via command line)
# ============================================

# Dot-notation path to Custom Prop (e.g., "userInfo.userId")
# Override via command line argument or set in environment
PROP_PATH = os.getenv("PROP_PATH", "")

# Optional: Filter results by value (substring match). Set to None to disable filtering.
# Override via command line argument or set in environment
VALUE_FILTER = os.getenv("VALUE_FILTER")  # None if not set

# Case-sensitive value filtering
CASE_SENSITIVE = os.getenv("CASE_SENSITIVE", "true").lower() == "true"

# Output format: "table", "json", "csv", or "values"
OUTPUT_FORMAT = "table"

# Directory containing event JSON files
EVENTS_DIR = Path("sentry_events")


def get_nested_value(data: Dict[str, Any], path: str) -> Any:
    """
    Get a nested value from a dictionary using dot notation.
    
    Args:
        data: The dictionary to search
        path: Dot-notation path (e.g., "userInfo.userId")
    
    Returns:
        The value at the path, or None if not found
    """
    keys = path.split(".")
    current = data
    
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return None
        
        if current is None:
            return None
    
    return current


def search_custom_props(
    events_dir: Path,
    prop_path: str,
    value_filter: Optional[str] = None,
    case_sensitive: bool = True
) -> List[Dict[str, Any]]:
    """
    Search through event JSON files for Custom Prop values.
    
    Args:
        events_dir: Directory containing event JSON files
        prop_path: Dot-notation path to the Custom Prop (e.g., "userInfo.userId")
        value_filter: Optional value to filter by (exact match or substring)
        case_sensitive: Whether value filtering is case sensitive
    
    Returns:
        List of dictionaries with event_id, file_path, and the matched value
    """
    if not events_dir.exists():
        print(f"Error: Events directory not found: {events_dir}")
        return []
    
    results = []
    json_files = list(events_dir.glob("*.json"))
    
    if not json_files:
        print(f"No JSON files found in {events_dir}")
        return []
    
    print(f"Searching {len(json_files)} event files for Custom Prop: {prop_path}")
    if value_filter:
        print(f"Filtering by value: {value_filter} (case_sensitive={case_sensitive})")
    
    for json_file in json_files:
        try:
            with json_file.open("r", encoding="utf-8") as f:
                event_data = json.load(f)
            
            # Navigate to Custom props
            custom_props = event_data.get("contexts", {}).get("Custom props", {})
            
            if not custom_props:
                continue
            
            # Get the value using dot notation
            value = get_nested_value(custom_props, prop_path)
            
            if value is None:
                continue
            
            # Apply value filter if provided
            if value_filter:
                value_str = str(value)
                filter_str = value_filter if case_sensitive else value_filter.lower()
                check_str = value_str if case_sensitive else value_str.lower()
                
                if filter_str not in check_str:
                    continue
            
            # Extract event ID from filename or event data
            event_id = json_file.stem  # filename without .json extension
            if not event_id:
                event_id = event_data.get("id", "unknown")
            
            results.append({
                "event_id": event_id,
                "file_path": str(json_file),
                "value": value,
                "prop_path": prop_path,
            })
            
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to read {json_file}: {e}", file=sys.stderr)
            continue
    
    return results


def print_results(results: List[Dict[str, Any]], output_format: str = "table"):
    """
    Print search results in various formats.
    
    Args:
        results: List of result dictionaries
        output_format: Format to use ("table", "json", "csv", "values")
    """
    if not results:
        print("\nNo matching events found.")
        return
    
    print(f"\nFound {len(results)} matching event(s):\n")
    
    if output_format == "json":
        print(json.dumps(results, indent=2))
    
    elif output_format == "csv":
        print("event_id,prop_path,value,file_path")
        for r in results:
            value = str(r["value"]).replace(",", ";")  # Escape commas
            print(f"{r['event_id']},{r['prop_path']},{value},{r['file_path']}")
    
    elif output_format == "values":
        # Just print unique values
        unique_values = sorted(set(str(r["value"]) for r in results))
        for val in unique_values:
            print(val)
    
    else:  # table format (default)
        # Find the longest value for formatting
        max_id_len = max(len(r["event_id"]) for r in results)
        max_value_len = max(len(str(r["value"])) for r in results)
        
        print(f"{'Event ID':<{max_id_len}} | {'Value':<{max_value_len}} | File")
        print("-" * (max_id_len + max_value_len + 50))
        
        for r in results:
            print(f"{r['event_id']:<{max_id_len}} | {str(r['value']):<{max_value_len}} | {r['file_path']}")


def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Search Sentry event JSON files for Custom Prop values",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for userId values
  %(prog)s userInfo.userId
  
  # Search and filter by specific value
  %(prog)s userInfo.userId --value "12345"
  
  # Case-insensitive search
  %(prog)s userInfo.userName --value "john" --case-insensitive
  
  # Output as JSON
  %(prog)s userInfo.userId --format json
  
  # Output just unique values
  %(prog)s userInfo.userId --format values
        """
    )
    
    parser.add_argument(
        "prop_path",
        nargs="?",
        default=PROP_PATH if PROP_PATH else None,
        help="Dot-notation path to Custom Prop (required if not set in config or env)"
    )
    
    parser.add_argument(
        "--value",
        dest="value_filter",
        default=None,
        help=f"Filter results by value (default from config: {VALUE_FILTER})"
    )
    
    parser.add_argument(
        "--case-insensitive",
        action="store_true",
        help="Case-insensitive value filtering (overrides config)"
    )
    
    parser.add_argument(
        "--format",
        choices=["table", "json", "csv", "values"],
        default=None,
        help=f"Output format (default from config: {OUTPUT_FORMAT})"
    )
    
    parser.add_argument(
        "--events-dir",
        type=Path,
        default=EVENTS_DIR,
        help=f"Directory containing event JSON files (default: {EVENTS_DIR})"
    )
    
    args = parser.parse_args()
    
    # Use config defaults if not provided via CLI
    prop_path = args.prop_path or PROP_PATH
    if not prop_path:
        parser.error("prop_path is required. Provide it as an argument or set PROP_PATH in environment/config.")
    
    value_filter = args.value_filter if args.value_filter is not None else VALUE_FILTER
    case_sensitive = not args.case_insensitive if args.case_insensitive else CASE_SENSITIVE
    output_format = args.format or OUTPUT_FORMAT
    
    # Perform search
    results = search_custom_props(
        events_dir=args.events_dir,
        prop_path=prop_path,
        value_filter=value_filter,
        case_sensitive=case_sensitive
    )
    
    # Print results
    print_results(results, output_format=output_format)


if __name__ == "__main__":
    main()

