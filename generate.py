#!/usr/bin/env python
import json
import os
import sys
import argparse
import logging
from typing import Tuple, Dict, List
import pandas as pd

from config import CATEGORIES, DEFAULT_MODEL, DATA_DIR, RESULTS_DIR, LOG_LEVEL, LOG_FORMAT
from lib.reviews import PlayStoreReviews
from lib.openai import OpenAIClient as LLMClient
from lib.validation import validate_review_data, validate_date_range, validate_classification
from lib.utils import clean_for_json, NpEncoder, get_next_date_range, group_classifications, create_summary_entry

# Setup logging
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)


def load_data_from_bigquery(start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch play store reviews from BigQuery"""
    logger.info(f"Loading data from BigQuery for {start_date} to {end_date}")
    review_client = PlayStoreReviews()
    review_client.fetch(start_date, end_date)
    reviews = review_client.data()
    
    if reviews is None:
        logger.error("Failed to fetch reviews from BigQuery")
        raise ValueError("No reviews returned from BigQuery")
    
    reviews['Translated_Text'] = None
    logger.info(f"Loaded {len(reviews)} reviews from BigQuery")
    return reviews

def load_data_from_file(filename: str) -> pd.DataFrame:
    """Load play store reviews from file"""
    logger.info(f"Loading data from file: {filename}")
    review_client = PlayStoreReviews()
    review_client.load(filename)
    reviews = review_client.data()
    
    if reviews is None:
        logger.error(f"Failed to load reviews from {filename}")
        raise ValueError(f"No reviews loaded from {filename}")
    
    reviews['Translated_Text'] = None
    logger.info(f"Loaded {len(reviews)} reviews from file")
    return reviews

def classify_reviews(reviews: pd.DataFrame, model: LLMClient) -> pd.DataFrame:
    """Translate and classify reviews using LLM"""
    total_reviews = len(reviews)
    logger.info(f"Starting classification of {total_reviews} reviews")
    
    for index, row in reviews.iterrows():
        # Progress tracking
        if (index + 1) % 10 == 0 or index == 0:
            logger.info(f"Processing review {index + 1}/{total_reviews} ({((index + 1)/total_reviews)*100:.1f}%)")
        
        rating = row['Star_Rating']
        src_lang = row['Reviewer_Language']
        text = row['Review_Text']

        logger.debug("-" * 75)
        logger.debug(f"Rating = {rating}")
        logger.debug(f"{row['Reviewer_Language']}: {row['Review_Text'][:100]}...")

        # Translate if not English
        if src_lang != 'en':
            try:
                text = model.translate(src_lang, 'en', row['Review_Text'])
                reviews.at[index, 'Translated_Text'] = text
                logger.debug(f"Translated: {text[:100]}...")
            except Exception as e:
                logger.error(f"Translation failed for review {index}: {e}")
                # Continue with original text
                text = row['Review_Text']

        # Classify the review
        try:
            classification = model.classify(rating, text, CATEGORIES)
            reviews.at[index, 'Classification'] = classification
            logger.debug(f"Classification: |{classification}|")
            
            # Validate classification
            if not validate_classification(classification, set(CATEGORIES.keys())):
                logger.warning(f"Invalid classification for review {index}: {classification}")
                
        except Exception as e:
            logger.error(f"Classification failed for review {index}: {e}")
            reviews.at[index, 'Classification'] = 'Other'
    
    logger.info(f"Completed classification of {total_reviews} reviews")
    return reviews


def parse_arguments() -> Tuple[argparse.ArgumentParser, argparse.Namespace]:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Translate and categorize play store reviews.')
    parser.add_argument('--input', type=str, default=None, help="Input filename that contains list of reviews in csv format.")
    parser.add_argument('--startDate', type=str, default=None, help="Start date of review list in YYYY-MM-DD.")
    parser.add_argument('--endDate', type=str, default=None, help="End date of review list in YYYY-MM-DD.")
    parser.add_argument('--summaryFile', type=str, required=True, help="Output JSON with per-week summaries.")
    args = parser.parse_args()
    return parser, args

def load_data_from_pickle(filename: str) -> pd.DataFrame:
    """Load data from pickle file"""
    logger.info(f"Loading pickled data from {filename}")
    try:
        return pd.read_pickle(filename)
    except Exception as e:
        logger.error(f"Failed to load pickle file {filename}: {e}")
        raise


def open_summary_file(filename: str) -> List[Dict]:
    """Open and parse summary JSON file"""
    if not os.path.isfile(filename):
        logger.error(f"Summary file does not exist: {filename}")
        sys.exit(1)
    
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"Loaded summary file with {len(data)} entries")
        return data
    except (OSError, json.JSONDecodeError) as e:
        logger.error(f"Error opening or parsing {filename}: {e}")
        sys.exit(1)

def verify_date_range(args: argparse.Namespace, summary_data: List[Dict], 
                      parser: argparse.ArgumentParser) -> Tuple[str, str]:
    """
    Return (start_date, end_date) while enforcing that the two flags are
    either BOTH present or BOTH absent.
    """
    # Case 1: neither flag supplied.  Get dates from summary file.
    if args.startDate is None and args.endDate is None:
        start_date, end_date = get_next_date_range(summary_data)

    # Case 2: both flags supplied, use given dates.
    elif args.startDate is not None and args.endDate is not None:
        start_date, end_date = args.startDate, args.endDate

    # Case 3: only one flag provided, raise an error.
    else:
        parser.error("--startDate and --endDate must be supplied together (or neither).")

    # Check if the summary data already has this result.
    for entry in summary_data:
        if entry["startDate"] == start_date and entry["endDate"] == end_date:
            parser.error(f"{start_date} -> {end_date} already exists in {args.summaryFile}")

    logger.info(f"Using date range: {start_date} -> {end_date}")
    return start_date, end_date


def main() -> None:
    """Main function to process Play Store reviews"""
    try:
        parser, args = parse_arguments()
        
        # Load or initialize summary data
        if os.path.isfile(args.summaryFile):
            summary_data = open_summary_file(args.summaryFile)
        else:
            summary_data = []
            logger.info("No existing summary file found, starting fresh")

        # Determine date range
        start_date, end_date = verify_date_range(args, summary_data, parser)
        
        # Setup file paths
        data_dir = os.path.join(DATA_DIR, f"{start_date}-to-{end_date}")
        reviews_output_filename = os.path.join(data_dir, "reviews.pkl")
        classify_output_filename = os.path.join(data_dir, "classify.pkl")
        results_output_filename = os.path.join(RESULTS_DIR, f"results-{start_date}-to-{end_date}.json")

        # Create directories if they don't exist
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(RESULTS_DIR, exist_ok=True)

        # Load review data
        if os.path.isfile(reviews_output_filename):
            logger.info("Loading cached review data")
            reviews = load_data_from_pickle(reviews_output_filename)
        elif args.input:
            reviews = load_data_from_file(args.input)
        else:
            reviews = load_data_from_bigquery(start_date, end_date)

        # Validate and clean data
        if reviews.empty:
            logger.warning(f"No reviews to process for date range: {start_date} -> {end_date}")
            sys.exit(0)
            
        reviews = validate_review_data(reviews)
        
        if reviews.empty:
            logger.warning(f"No valid reviews remaining after data cleaning for {start_date} -> {end_date}")
            sys.exit(0)

        # Validate date range
        reviews["Review_Submit_Date_and_Time"] = pd.to_datetime(
            reviews["Review_Submit_Date_and_Time"], errors="coerce"
        )
        
        if not validate_date_range(reviews, start_date, end_date):
            logger.error("Date range validation failed")
            sys.exit(1)

        # Cache reviews if validation passed
        reviews.to_pickle(reviews_output_filename)
        logger.info(f"Cached {len(reviews)} reviews to {reviews_output_filename}")

        # Classify reviews
        if os.path.isfile(classify_output_filename):
            logger.info("Loading cached classification data")
            reviews = load_data_from_pickle(classify_output_filename)
        else:
            model = LLMClient(DEFAULT_MODEL)
            reviews = classify_reviews(reviews, model)
            reviews.to_pickle(classify_output_filename)
            logger.info(f"Cached classified reviews to {classify_output_filename}")

        logger.info(f"Processing {len(reviews)} classified reviews")
        
        # Group classifications
        grouped_data = group_classifications(reviews, CATEGORIES)
        
        # Write results to disk
        logger.info(f"Writing results to {results_output_filename}")
        with open(results_output_filename, 'w') as f:
            data = clean_for_json(grouped_data)
            json.dump(data, f, indent=2, cls=NpEncoder, allow_nan=False)

        # Create and append summary entry
        entry = create_summary_entry(reviews, grouped_data, start_date, end_date)
        summary_data.append(entry)

        logger.info("New entry in summary file:")
        logger.info(json.dumps(entry, indent=2))

        # Save updated summary file
        with open(args.summaryFile, 'w') as f:
            json.dump(summary_data, f, indent=2)
        
        logger.info(f"Successfully processed reviews for {start_date} to {end_date}")
        
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

