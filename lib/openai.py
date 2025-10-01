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

  def classify(self, rating: int, text: str, categories: Dict[str, str], examples: list = None) -> str:
    """Classify review text into predefined categories"""
    self.logger.debug(f"Classifying review (rating: {rating}): {text[:50]}...")

    category_text = "\n".join(f"{key}: {desc}" for key, desc in categories.items())

    # Build few-shot examples section
    examples_text = ""
    if examples:
      examples_text = "\nHere are some examples to guide your classifications:\n\n"
      for i, example in enumerate(examples, 1):
        examples_text += f"Example {i}:\n"
        examples_text += f"Rating: {example['rating']}/5\n"
        examples_text += f"Review: \"{example['review']}\"\n"
        examples_text += f"Classification: {example['classification']}\n\n"

    messages = [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text":
f"""You are classifying a Google Play Store review for the Firefox browser with a star rating of {rating}/5.

CLASSIFICATION RULES:
1. If the review is mostly positive with no complaints, return 'Satisfied'
2. If there are negative complaints, classify them into the categories below
3. Multiple categories can apply - return a comma-separated list
4. IMPORTANT: If the user mentions a specific website having problems (like videos not playing on YouTube, Facebook not loading, etc.), you MUST include that website as a category
5. Only use 'Other' if no other categories apply

WEBSITE-SPECIFIC ISSUES:
When users report problems with specific websites, ALWAYS add the website name as a category in addition to the technical category.

Use these EXACT formats for common websites:
- YouTube (for youtube, Youtube, youtube.com, yt, etc.)
- Facebook (for facebook, FB, fb, facebook.com, etc.)
- Google (for google, google.com, Google.com, etc.)
- Reddit (for reddit, reddit.com, etc.)
- Instagram (for instagram, IG, ig, insta, etc.)
- Twitter (for twitter, X, x.com, twitter.com, etc.)
- TikTok (for tiktok, Tiktok, etc.)
- Netflix (for netflix, etc.)
- Amazon (for amazon, amazon.com, etc.)
- WhatsApp (for whatsapp, Whatsapp, etc.)

For other websites: use proper case (first letter capitalized, no .com/.org extensions)

Examples of website categorization:
- "YouTube videos won't play" → Youtube, Video
- "Facebook keeps crashing" → Facebook, Crash
- "Instagram stories don't load" → Instagram, Webcompat
- "Can't watch Netflix" → Netflix, Video

TECHNICAL CATEGORIES:
{category_text}
{examples_text}
Now classify this review:

Rating: {rating}/5
Review: {text}

Classification:"""
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
