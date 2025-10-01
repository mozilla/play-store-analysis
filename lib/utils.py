"""Utility functions for Play Store Analysis"""
import json
import math
import re
import logging
from typing import Any, Dict, List, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd


logger = logging.getLogger(__name__)


# Common website patterns and their canonical names
WEBSITE_PATTERNS = {
    'YouTube': [
        r'\byoutube\b', r'\byt\b', r'\byoutube\.com\b', r'\byoutube\s',
        r'\byoutubes\b', r'\byoutub\b'
    ],
    'Facebook': [
        r'\bfacebook\b', r'\bfb\b', r'\bfacebook\.com\b', r'\bface\s?book\b',
        r'\bfacebooks\b'
    ],
    'Instagram': [
        r'\binstagram\b', r'\binsta\b', r'\big\b', r'\binstagram\.com\b',
        r'\binstagrams\b'
    ],
    'Twitter': [
        r'\btwitter\b', r'\btwitter\.com\b', r'\bx\.com\b',
        r'\btweets?\b', r'\btwitting\b'
    ],
    'TikTok': [
        r'\btiktok\b', r'\btik\s?tok\b', r'\btiktok\.com\b'
    ],
    'Netflix': [
        r'\bnetflix\b', r'\bnetflix\.com\b'
    ],
    'Reddit': [
        r'\breddit\b', r'\breddit\.com\b', r'\bsubreddit\b'
    ],
    'Google': [
        r'\bgoogle\b', r'\bgoogle\.com\b', r'\bgoogling\b'
    ],
    'Amazon': [
        r'\bamazon\b', r'\bamazon\.com\b', r'\bamzn\b'
    ],
    'WhatsApp': [
        r'\bwhatsapp\b', r'\bwhats\s?app\b', r'\bwa\b'
    ],
    'Spotify': [
        r'\bspotify\b', r'\bspotify\.com\b'
    ],
    'Discord': [
        r'\bdiscord\b', r'\bdiscord\.com\b'
    ],
    'Twitch': [
        r'\btwitch\b', r'\btwitch\.tv\b'
    ],
    'LinkedIn': [
        r'\blinkedin\b', r'\blinkedin\.com\b'
    ],
    'Pinterest': [
        r'\bpinterest\b', r'\bpinterest\.com\b'
    ]
}


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
    rating_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

    # Count total positive and negative reviews.  This is tricky, since
    # a 5 star review can still contain negative comments we care about.
    # We follow these guidelines:
    #   - If the LLM thinks it's positive, we mark it as positive.
    #   - Else if the review is a 3/5 or less, it's negative.
    #   - Else if there is a classification other than "Other", it's negative.
    for index, row in reviews.iterrows():
        # Count ratings
        rating = row['Star_Rating']
        if rating in rating_counts:
            rating_counts[rating] += 1

        # Count positive/negative
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
        "Categories": {},
        "Ratings": {
            "1": rating_counts[1],
            "2": rating_counts[2],
            "3": rating_counts[3],
            "4": rating_counts[4],
            "5": rating_counts[5]
        }
    }

    # Fill in the counts for each category.
    for category in grouped_data:
        entry["Categories"][category] = len(grouped_data[category])

    logger.info(f"Created summary entry: {positive_count} positive, {negative_count} negative reviews")
    logger.info(f"Rating counts: {rating_counts}")
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


def detect_websites_in_text(text: str) -> set:
    """
    Detect website mentions in review text.

    Returns a set of canonical website names found in the text.
    """
    if not text:
        return set()

    text_lower = text.lower()
    detected_websites = set()

    for website, patterns in WEBSITE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                detected_websites.add(website)
                break

    return detected_websites


def enhance_classification_with_websites(classification: str, review_text: str) -> str:
    """
    Enhance classification by adding detected websites that were missed.

    Args:
        classification: Current classification string (comma-separated)
        review_text: Original review text

    Returns:
        Enhanced classification string with detected websites added
    """
    if not classification or not review_text:
        return classification

    # Get current categories
    current_categories = set(cat.strip() for cat in classification.split(','))

    # Detect websites in text
    detected_websites = detect_websites_in_text(review_text)

    # Find missing websites
    missing_websites = detected_websites - current_categories

    if missing_websites:
        logger.info(f"Adding missing website categories: {missing_websites}")
        # Add missing websites to classification
        all_categories = list(current_categories) + list(missing_websites)
        return ', '.join(all_categories)

    return classification