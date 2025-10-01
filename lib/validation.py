"""Data validation utilities for Play Store Analysis"""
import logging
from datetime import datetime, date
from typing import Optional
import pandas as pd


logger = logging.getLogger(__name__)


def validate_review_data(reviews: pd.DataFrame) -> pd.DataFrame:
    """Clean and validate review data, removing bad reviews"""
    required_columns = [
        'Package_Name', 'App_Version_Name', 'Reviewer_Language', 'Device',
        'Review_Submit_Date_and_Time', 'Star_Rating', 'Review_Text', 'Review_Link'
    ]
    
    original_count = len(reviews)
    logger.info(f"Starting validation with {original_count} reviews")
    
    # Check for required columns
    missing_columns = [col for col in required_columns if col not in reviews.columns]
    if missing_columns:
        logger.error(f"Missing required columns: {missing_columns}")
        raise ValueError(f"Missing required columns: {missing_columns}")
    
    # Check for empty dataframe
    if reviews.empty:
        logger.warning("Review dataframe is empty")
        return reviews
    
    # Remove reviews with invalid star ratings
    valid_ratings = reviews['Star_Rating'].between(1, 5)
    invalid_ratings_count = (~valid_ratings).sum()
    if invalid_ratings_count > 0:
        logger.warning(f"Removing {invalid_ratings_count} reviews with invalid star ratings")
        reviews = reviews[valid_ratings]
    
    # Remove reviews with null review text
    valid_text = reviews['Review_Text'].notna() & (reviews['Review_Text'].str.strip() != '')
    null_text_count = (~valid_text).sum()
    if null_text_count > 0:
        logger.warning(f"Removing {null_text_count} reviews with null or empty text")
        reviews = reviews[valid_text]
    
    # Clean dates and remove invalid ones
    try:
        reviews['Review_Submit_Date_and_Time'] = pd.to_datetime(
            reviews['Review_Submit_Date_and_Time'], errors='coerce'
        )
        valid_dates = reviews['Review_Submit_Date_and_Time'].notna()
        invalid_dates_count = (~valid_dates).sum()
        if invalid_dates_count > 0:
            logger.warning(f"Removing {invalid_dates_count} reviews with invalid dates")
            reviews = reviews[valid_dates]
    except Exception as e:
        logger.error(f"Error processing dates: {e}")
        raise

    final_count = len(reviews)
    removed_count = original_count - final_count
    logger.info(f"Validation completed: kept {final_count} reviews, removed {removed_count} bad reviews")
    
    return reviews.reset_index(drop=True)


def validate_date_range(reviews: pd.DataFrame, start_date: str, end_date: str) -> bool:
    """Validate that reviews fall within the expected date range"""
    try:
        expected_start = date.fromisoformat(start_date)
        expected_end = date.fromisoformat(end_date)
        
        # Get actual date range from data
        reviews_start = reviews["Review_Submit_Date_and_Time"].iloc[-1].date()
        reviews_end = reviews["Review_Submit_Date_and_Time"].iloc[0].date()
        
        if reviews_start != expected_start or reviews_end != expected_end:
            logger.error(
                f"Date range mismatch:\n"
                f"  expected {start_date} → {end_date}\n"
                f"  got      {reviews_start} → {reviews_end}"
            )
            return False
        
        logger.info(f"Date range validation passed: {start_date} → {end_date}")
        return True
        
    except Exception as e:
        logger.error(f"Error validating date range: {e}")
        return False


def validate_classification(classification: str, valid_categories: set) -> bool:
    """Validate that classification contains only valid categories"""
    if not classification:
        logger.warning("Empty classification received")
        return False
    
    categories = [cat.strip() for cat in classification.split(',')]
    invalid_categories = []
    for cat in categories:
        if cat not in valid_categories and not _is_website_category(cat):
            invalid_categories.append(cat)
    
    if invalid_categories:
        logger.warning(f"New categories found: {invalid_categories}")
        # Don't return False as we want to allow new website categories
    
    return True


def _is_website_category(category: str) -> bool:
    """Check if category appears to be a website name"""
    # Simple heuristic: starts with capital letter, no spaces, reasonable length
    return (
        category and
        category[0].isupper() and
        ' ' not in category and
        2 <= len(category) <= 20 and
        category.replace('.', '').isalnum()
    )


def validate_classification_logic(rating: int, classification: str) -> bool:
    """
    Validate that classification makes logical sense given the star rating.

    Returns False if classification is suspicious (e.g., high rating with negative categories).
    This doesn't prevent the classification but logs a warning for review.
    """
    if not classification:
        return True

    # Define negative categories that shouldn't appear with high ratings
    negative_categories = {
        'Crash', 'Slow', 'Battery', 'Memory', 'Pageload', 'Webcompat',
        'Networking', 'Stuttering', 'Scrolling', 'Startup', 'UI',
        'Downloads', 'Autofill', 'Search', 'History', 'Audio', 'Video'
    }

    categories = [cat.strip() for cat in classification.split(',')]

    # Check for suspicious patterns
    # Pattern 1: High rating (4-5 stars) with negative categories
    if rating >= 4:
        found_negative = [cat for cat in categories if cat in negative_categories]
        if found_negative:
            logger.warning(
                f"Suspicious: High rating ({rating} stars) with negative categories: {found_negative}"
            )
            return False

    # Pattern 2: Low rating (1-2 stars) classified as "Satisfied" only
    if rating <= 2 and categories == ['Satisfied']:
        logger.warning(
            f"Suspicious: Low rating ({rating} stars) classified only as 'Satisfied'"
        )
        return False

    # Pattern 3: 5-star rating with only negative categories (no Satisfied)
    if rating == 5 and 'Satisfied' not in categories:
        found_negative = [cat for cat in categories if cat in negative_categories]
        if found_negative and len(found_negative) == len(categories):
            logger.warning(
                f"Suspicious: 5-star rating with only negative categories: {found_negative}"
            )
            return False

    return True