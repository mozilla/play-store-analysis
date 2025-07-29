# Play Store Analysis

A tool for analyzing Mozilla Firefox Play Store reviews using AI classification. This project fetches Firefox app reviews from Google BigQuery, translates non-English reviews, and classifies them into predefined categories using OpenAI's API.

## Features

- **Review Fetching**: Retrieves Firefox app reviews from Google BigQuery
- **Multi-language Support**: Translates non-English reviews to English
- **AI Classification**: Categorizes reviews into 22+ predefined categories (Webcompat, Performance, Privacy, etc.)
- **Web Dashboard**: Interactive HTML dashboard for visualizing results
- **Weekly Analysis**: Processes reviews in weekly batches with trend analysis

## Prerequisites

- Python 3.10+
- OpenAI API key
- Google Cloud credentials (for BigQuery access)
- Docker (optional)

## Installation & Setup

### Local Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd play-store-analysis
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up authentication**:
   ```bash
   # Set OpenAI API key
   export OPENAI_API_KEY="your-openai-api-key"
   
   # Authenticate with Google Cloud
   gcloud auth login
   gcloud auth application-default login
   ```

## Usage

### Command Line Interface

**Basic usage** (processes next week in sequence):
```bash
python generate.py --summaryFile results/review-summary.json
```

**Specify date range**:
```bash
python generate.py \
  --startDate 2024-01-01 \
  --endDate 2024-01-07 \
  --summaryFile results/review-summary.json
```

**Process from CSV file**:
```bash
python generate.py \
  --input data/reviews.csv \
  --startDate 2024-01-01 \
  --endDate 2024-01-07 \
  --summaryFile results/review-summary.json
```

### Docker Usage

**Run analysis with default settings**:
```bash
docker run --rm \
  -e OPENAI_API_KEY="your-api-key" \
  -v ~/.config/gcloud:/root/.config/gcloud:ro \
  -v $(pwd)/results:/app/results \
  play-store-analysis
```

**Run with custom date range**:
```bash
docker run --rm \
  -e OPENAI_API_KEY="your-api-key" \
  -v ~/.config/gcloud:/root/.config/gcloud:ro \
  -v $(pwd)/results:/app/results \
  play-store-analysis \
  conda run -n play-store-analysis python generate.py \
    --startDate 2024-01-01 \
    --endDate 2024-01-07 \
    --summaryFile results/review-summary.json
```

**Run with local data file**:
```bash
docker run --rm \
  -e OPENAI_API_KEY="your-api-key" \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/results:/app/results \
  play-store-analysis \
  conda run -n play-store-analysis python generate.py \
    --input data/reviews.csv \
    --startDate 2024-01-01 \
    --endDate 2024-01-07 \
    --summaryFile results/review-summary.json
```

## Configuration

The main configuration is in `config.py`:

- **LLM Settings**: Model selection, API keys, rate limiting
- **BigQuery**: Project, dataset, and table configuration
- **Firefox Apps**: Package names to analyze
- **Categories**: 22 predefined review classification categories
- **File Paths**: Data and results directory locations

### Key Categories

The system classifies reviews into these categories:
- **Technical**: Webcompat, Slow, Pageload, Memory, Battery, Crash
- **Features**: Tabs, Addons, Bookmarks, Sync, Translations
- **Media**: Audio, Video, Stuttering
- **UI/UX**: UI, Scrolling, Startup
- **Other**: Privacy, Policy, Networking, Benchmark, Satisfied

## Output Files

The tool generates several output files:

- **`results/review-summary.json`**: Summary statistics for all processed weeks
- **`results/results-YYYY-MM-DD-to-YYYY-MM-DD.json`**: Detailed results for each week
- **`data/YYYY-MM-DD-to-YYYY-MM-DD/reviews.pkl`**: Cached raw review data
- **`data/YYYY-MM-DD-to-YYYY-MM-DD/classify.pkl`**: Cached classified review data

## Web Dashboard

Open `index.html` in a web browser to view the interactive dashboard:

1. **Overview**: Trend charts showing positive vs negative reviews and category trends
2. **Week Compare**: Side-by-side comparison of two weeks with difference analysis
3. **Reviews**: Searchable table of individual reviews with filtering options

The dashboard requires the `results/` directory with generated JSON files.

## Development

### Project Structure
```
play-store-analysis/
├── config.py              # Configuration settings
├── generate.py             # Main analysis script
├── entry.sh               # Docker entry script
├── index.html             # Web dashboard
├── requirements.txt       # Python dependencies
├── Dockerfile             # Container definition
├── lib/
│   ├── openai.py          # OpenAI API client
│   ├── reviews.py         # BigQuery data fetching
│   ├── utils.py           # Utility functions
│   └── validation.py      # Data validation
├── data/                  # Cached review data
└── results/               # Analysis results
```

### Adding New Categories

1. Edit the `CATEGORIES` dictionary in `config.py`
2. Add the category name and description
3. The AI will automatically classify reviews into the new category

### Rate Limiting

The tool includes built-in rate limiting for API calls:
- 0.5 second delay between requests (configurable)
- 3 retry attempts with exponential backoff
- Progress logging every 10 reviews

## License

See LICENSE file for details.
