#!/bin/bash
set -euxo pipefail

# Create results directory if it doesn't exist
mkdir -p results

echo -e "\n*************************************************"
echo -e "Copying review-summary.json from GCS\n"
gsutil cp $BUCKET_URL/results/review-summary.json results/review-summary.json
cp results/review-summary.json results/review-summary-backup.json

echo -e "\n*************************************************"
echo -e "Generating new analysis...\n"
python generate.py --summaryFile results/review-summary.json

# Check if review-summary.json was modified
if ! cmp -s results/review-summary.json results/review-summary-backup.json; then
  echo -e "\n*************************************************"
  echo -e "Changes detected - uploading updated files\n"
  
  # Upload the updated summary file
  gsutil cp results/review-summary.json $BUCKET_URL/results/review-summary.json
  
  # Find and upload the new results file
  # Extract the latest entry's file name from the summary
  NEW_RESULTS_FILE=$(python -c "
import json
with open('results/review-summary.json', 'r') as f:
    data = json.load(f)
    print(data[-1]['file'])
  ")
  
  if [ -f "results/$NEW_RESULTS_FILE" ]; then
    echo -e "Uploading new results file: $NEW_RESULTS_FILE"
    gsutil cp results/$NEW_RESULTS_FILE $BUCKET_URL/results/$NEW_RESULTS_FILE
  fi
  
  echo -e "Upload complete\n"
else
  echo -e "\n*************************************************"
  echo -e "No changes detected - nothing to upload\n"
fi
