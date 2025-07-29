"""Utility functions for Play Store Analysis"""
import json
import math
import logging
from typing import Any, Dict, List, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd


logger = logging.getLogger(__name__)


def clean_for_json(obj: Any) -> Any:
    """Clean object for JSON serialization by handling numpy types and NaN values"""
    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_for_json(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(clean_for_json(item) for item in obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return None if math.isnan(obj) or math.isinf(obj) else float(obj)
    elif isinstance(obj, float):
        return None if math.isnan(obj) or math.isinf(obj) else obj
    elif isinstance(obj, np.ndarray):
        return clean_for_json(obj.tolist())
    else:
        return obj


class NpEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy types and NaN values"""
    def default(self, obj: Any) -> Any:
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            # Convert NaN to None
            if math.isnan(obj):
                return None
            return float(obj)
        if isinstance(obj, float) and math.isnan(obj):
            return None
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def get_next_date_range(summary_data: List[Dict]) -> Tuple[str, str]:
    """
    Get the next week from the summary file. Return as Tuple.
    """
    if not summary_data:
        logger.error("JSON is empty; cannot determine next week.")
        raise ValueError("Empty summary data")

    # Calculate the next week to generate data for.
    last = summary_data[-1]
    try:
        last_start = datetime.strptime(last["startDate"], "%Y-%m-%d")
        # You can derive end date either from JSON or via +6 days
        next_start = last_start + timedelta(days=7)
        next_end = next_start + timedelta(days=6)
    except (KeyError, ValueError) as e:
        logger.error(f"Invalid or missing 'startDate' in JSON ({e})")
        raise

    return (
        next_start.strftime("%Y-%m-%d"),
        next_end.strftime("%Y-%m-%d"),
    )


def group_classifications(reviews: pd.DataFrame, categories: Dict[str, str]) -> Dict[str, List[Dict]]:
    """Group reviews by their classifications"""
    results = {}
    logger.info(f"Grouping classifications for {len(reviews)} reviews")
    
    for index, row in reviews.iterrows():
        entry = {
            'device': row['Device'],
            'version': row['App_Version_Name'],
            'package': row['Package_Name'],
            'rating': row['Star_Rating'],
            'language': row['Reviewer_Language'],
            'text': row['Review_Text'],
            'translated': row.get('Translated_Text'),
            'link': row['Review_Link']
        }

        classification = row['Classification'].split(',')
        for cat in classification:
            cat = cat.strip()
            if cat not in categories and not _is_valid_website_category(cat):
                logger.warning(f"Unknown category found: {cat}")
                continue
            results.setdefault(cat, []).append(entry)
    
    # Log category counts
    for category, reviews_list in results.items():
        logger.info(f"{category}: {len(reviews_list)} reviews")
    
    return results


def create_summary_entry(reviews: pd.DataFrame, grouped_data: Dict[str, List], 
                        start_date: str, end_date: str) -> Dict:
    """Create summary entry for the processed reviews"""
    positive_count = 0
    negative_count = 0

    # Count total positive and negative reviews.  This is tricky, since
    # a 5 star review can still contain negative comments we care about.
    # We follow these guidelines:
    #   - If the LLM thinks it's positive, we mark it as positive.
    #   - Else if the review is a 3/5 or less, it's negative.
    #   - Else if there is a classification other than "Other", it's negative.
    for index, row in reviews.iterrows():
        if row['Classification'].lower() == "satisfied":
            positive_count += 1
        elif row['Star_Rating'] <= 3:
            negative_count += 1
        elif row['Classification'].lower() != 'other':
            negative_count += 1

    entry = {
        "startDate": start_date,
        "endDate": end_date,
        "file": f"results-{start_date}-to-{end_date}.json",
        "PositiveCount": positive_count,
        "NegativeCount": negative_count,
        "Categories": {}
    }
    
    # Fill in the counts for each category.
    for category in grouped_data:
        entry["Categories"][category] = len(grouped_data[category])
    
    logger.info(f"Created summary entry: {positive_count} positive, {negative_count} negative reviews")
    return entry


def _is_valid_website_category(category: str) -> bool:
    """Check if category appears to be a valid website name"""
    # Simple heuristic: starts with capital letter, no spaces, reasonable length
    return (
        category and
        category[0].isupper() and
        ' ' not in category and
        2 <= len(category) <= 20 and
        category.replace('.', '').replace('-', '').isalnum()
    )