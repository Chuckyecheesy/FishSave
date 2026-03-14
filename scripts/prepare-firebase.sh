#!/usr/bin/env bash
# Copy static assets into public/ for Firebase Hosting deploy.
# Run from project root: ./scripts/prepare-firebase.sh

set -e
cd "$(dirname "$0")/.."

mkdir -p public
cp index.html public/
cp forecast_next5years.csv public/
cp risk_score_with_category.csv public/
cp -r graphs_5y public/
cp -r graphs_10y public/

echo "Done. public/ is ready for: firebase deploy --only hosting"
