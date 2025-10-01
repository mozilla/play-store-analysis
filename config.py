"""Configuration settings for Play Store Analysis"""
from typing import Dict
import os

# LLM Configuration
DEFAULT_MODEL = "gpt-4o"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
RATE_LIMIT_DELAY = 0.5  # seconds between API calls
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# BigQuery Configuration
BIGQUERY_PROJECT = "mozdata"
BIGQUERY_DATASET = "google_play_store"
BIGQUERY_TABLE = "reviews"

# Package names to analyze
PACKAGE_NAMES = [
    'org.mozilla.firefox',
    'org.mozilla.firefox_beta', 
    'org.mozilla.fenix'
]

# File paths
DATA_DIR = "data"
RESULTS_DIR = "results"

# Review classification categories
CATEGORIES: Dict[str, str] = {
    "Webcompat"   : "Website functionality or rendering problems. User may also report websites work in other browsers",
    "Slow"        : "General slowness or performance lag when using the browser",
    "Privacy"     : "Concerns about tracking, data collection, or permissions",
    "Policy"      : "Store or terms-of-service / content-policy issues",
    "Pageload"    : "Slow page-load times",
    "Audio"       : "Audio playback or recording problems",
    "Video"       : "Video playback or streaming problems",
    "Networking"  : "Connectivity, proxy, or offline-mode issues",
    "Battery"     : "Excessive battery drain or power use",
    "Memory"      : "High RAM usage or memory leaks",
    "Sync"        : "Account, bookmark, or settings sync failures",
    "Tabs"        : "Issues with tab reloading or tab performance, or any tab features",
    "Addons"      : "Anything negative related to addons or extensions",
    "Benchmark"   : "Performance test or benchmark comparisons",
    "Bookmarks"   : "Anything negative related to bookmarks",
    "Translations": "Automatic or manual page translation issues",
    "Crash"       : "Browser or tab crashes and hangs",
    "Scrolling"   : "Jumping, jittery, or non-smooth scrolling",
    "Stuttering"  : "Video or animation stutter / dropped frames",
    "Startup"     : "Slow launch or loading of browser itself",
    "UI"          : "User-interface layout or visual glitches",
    "Downloads"   : "Issues with downloading files or download manager",
    "Autofill"    : "Problems with password saving, autofill, or form filling",
    "Search"      : "Search engine, search bar, or address bar search issues",
    "History"     : "Browsing history problems or history management issues",
    "Satisfied"   : "Positive feedback / feature praise",
    "Other"       : "Anything not covered by the above categories",
}

# Few-shot examples for classification
CLASSIFICATION_EXAMPLES = [
    {
        "review": "Pages take forever to load, very slow performance",
        "rating": 2,
        "classification": "Pageload"
    },
    {
        "review": "Love the privacy features and ad blocking! Best browser ever",
        "rating": 5,
        "classification": "Satisfied"
    },
    {
        "review": "Crashes when I open too many tabs. Very frustrating",
        "rating": 1,
        "classification": "Crash, Tabs"
    },
    {
        "review": "Battery drains fast when using this browser",
        "rating": 2,
        "classification": "Battery"
    },
    {
        "review": "YouTube videos don't play properly, they stutter and freeze",
        "rating": 1,
        "classification": "YouTube, Video, Stuttering"
    },
    {
        "review": "Facebook won't load properly, keeps showing blank page",
        "rating": 2,
        "classification": "Facebook, Webcompat"
    },
    {
        "review": "Instagram stories don't work at all",
        "rating": 1,
        "classification": "Instagram, Webcompat"
    },
    {
        "review": "Can't download PDFs. Download button doesn't work",
        "rating": 2,
        "classification": "Downloads"
    },
    {
        "review": "Password autofill stopped working after update",
        "rating": 3,
        "classification": "Autofill"
    },
    {
        "review": "UI is laggy and some websites don't render correctly",
        "rating": 2,
        "classification": "UI, Webcompat, Slow"
    }
]

# Logging configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
