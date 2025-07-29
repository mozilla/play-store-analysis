import re
import sys
import time
import logging
from typing import Dict
from openai import OpenAI
from config import MAX_RETRIES, RETRY_DELAY, RATE_LIMIT_DELAY, OPENAI_API_KEY

class OpenAIClient:
  def __init__(self, model: str):
    self.model = model
    self.logger = logging.getLogger(__name__)
    
    if not OPENAI_API_KEY:
      self.logger.error("OPENAI_API_KEY must be defined")
      sys.exit(1)

    self.client = OpenAI(api_key=OPENAI_API_KEY)
    self.logger.info(f"Initialized OpenAI client with model: {model}")


  def _make_api_call_with_retry(self, messages: list):
    """Make OpenAI API call with retry logic and rate limiting"""
    for attempt in range(MAX_RETRIES):
      try:
        time.sleep(RATE_LIMIT_DELAY)  # Rate limiting
        completion = self.client.chat.completions.create(
          model=self.model,
          messages=messages
        )
        return completion
      except Exception as e:
        self.logger.warning(f"API call attempt {attempt + 1} failed: {e}")
        if attempt == MAX_RETRIES - 1:
          self.logger.error(f"All {MAX_RETRIES} API call attempts failed")
          raise
        time.sleep(RETRY_DELAY * (attempt + 1))  # Exponential backoff
    
    raise Exception("Unexpected error in API retry logic")

  def translate(self, src_lang: str, dst_lang: str, text: str) -> str:
    """Translate text from source language to destination language"""
    self.logger.debug(f"Translating from {src_lang} to {dst_lang}: {text[:50]}...")
    
    messages = [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": f"Translate the following from {src_lang} to {dst_lang}.  Do not provide any analysis or explanation, just the direct translation as the answer.  Text is:  \"{text}\""
          },
        ]
      }
    ]
    
    try:
      completion = self._make_api_call_with_retry(messages)
      content = completion.choices[0].message.content
      if not content:
        raise ValueError("Empty response from OpenAI API")
      
      answer = re.sub(r"<think>.*?</think>\s*", "", content, flags=re.DOTALL)
      self.logger.debug(f"Translation result: {answer[:50]}...")
      return answer
    except Exception as e:
      self.logger.error(f"Translation failed for text: {text[:50]}... Error: {e}")
      raise

  def classify(self, rating: int, text: str, categories: Dict[str, str]) -> str:
    """Classify review text into predefined categories"""
    self.logger.debug(f"Classifying review (rating: {rating}): {text[:50]}...")
    
    category_text = "\n".join(f"{key}: {desc}" for key, desc in categories.items())
    messages = [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": 
f"""The following is a review from Google Play Store for the Firefox browser with a star rating of {rating}/5.  If the review is mostly positive, simply return 'Satisfied' for your classification.  If there are negative complaints in the review, I want to classify it into the following categories, or use the category "Other" if none match.  More than one category can apply, return a comma separated list.  Only use Other if no other categories apply.

For website-specific issues, use these exact formats:
- YouTube (not youtube, Youtube, or youtube.com)
- Facebook (not facebook, FB, or facebook.com)
- Google (not google, google.com, or Google.com)
- Reddit (not reddit, reddit.com)
- Instagram (not instagram, IG)
- Twitter (not twitter, X, twitter.com)
- TikTok (not tiktok, Tiktok)
- Netflix (not netflix)
- Amazon (not amazon, amazon.com)
- WhatsApp (not whatsapp, Whatsapp)

For other websites, use proper case format: first letter capitalized, no domain extensions (.com, .org, etc).

Categories:
{category_text}

Review:
{text}
"""
          },
        ]
      }
    ]
    
    try:
      completion = self._make_api_call_with_retry(messages)
      content = completion.choices[0].message.content
      if not content:
        raise ValueError("Empty response from OpenAI API")
      
      answer = re.sub(r"<think>.*?</think>\s*", "", content, flags=re.DOTALL)
      self.logger.debug(f"Classification result: {answer}")
      return answer
    except Exception as e:
      self.logger.error(f"Classification failed for text: {text[:50]}... Error: {e}")
      raise
