import os
import sys
import logging
from typing import Optional
import pandas as pd
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError
from config import BIGQUERY_PROJECT, PACKAGE_NAMES

class PlayStoreReviews:
  def __init__(self):
    self.logger = logging.getLogger(__name__)
    try:
      self.client = bigquery.Client(project=BIGQUERY_PROJECT)
      self.logger.info(f"Initialized BigQuery client for project: {BIGQUERY_PROJECT}")
    except Exception as e:
      self.logger.error(f"Failed to initialize BigQuery client: {e}")
      raise
    self.reviews: Optional[pd.DataFrame] = None

  def fetch(self, start_date: str, end_date: str) -> None:
    """Fetch reviews from BigQuery for the specified date range"""
    self.logger.info(f"Fetching reviews from {start_date} to {end_date}")
    
    package_list = "', '".join(PACKAGE_NAMES)
    query = f"""
      SELECT
        Package_Name,
        App_Version_Name,
        Reviewer_Language,
        Device,
        Review_Submit_Date_and_Time,
        Star_Rating,
        Review_Text,
        Review_Link
      FROM
        `{BIGQUERY_PROJECT}.google_play_store.reviews` r
      WHERE
        DATE(Review_Submit_Date_and_Time) >= DATE('{start_date}')
        AND DATE(Review_Submit_Date_and_Time) <= DATE('{end_date}')
        AND Review_Text is not NULL
        AND Package_Name in ('{package_list}')
      ORDER BY
        Review_Submit_Date_and_Time DESC
    """
    
    try:
      self.logger.debug(f"Executing BigQuery: {query[:100]}...")
      job = self.client.query(query)
      df = job.to_dataframe()
      self.logger.info(f"Retrieved {len(df)} reviews")
      
      if df.empty:
        self.logger.warning(f"No reviews found for date range {start_date} to {end_date}")
      
      self.reviews = df
    except GoogleCloudError as e:
      self.logger.error(f"BigQuery error: {e}")
      raise
    except Exception as e:
      self.logger.error(f"Unexpected error fetching reviews: {e}")
      raise

  def load(self, filename: str) -> None:
    """Load reviews from a CSV file"""
    self.logger.info(f"Loading reviews from file: {filename}")
    
    try:
      if not os.path.exists(filename):
        raise FileNotFoundError(f"File not found: {filename}")
      
      self.reviews = pd.read_csv(filename)
      self.logger.info(f"Loaded {len(self.reviews)} reviews from {filename}")
    except Exception as e:
      self.logger.error(f"Failed to load reviews from {filename}: {e}")
      raise

  def data(self) -> Optional[pd.DataFrame]:
    """Get the loaded reviews data"""
    return self.reviews
