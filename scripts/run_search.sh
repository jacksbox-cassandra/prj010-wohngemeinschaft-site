#!/bin/bash
# PRJ010 Property Search - Automated Run Script
# Runs scraper, enrichment, website generation, and git push

set -e  # Exit on error

# Configuration
PROJECT_DIR="/Users/jacksbot/projects/PRJ010-wohngemeinschaft"
LOG_FILE="${PROJECT_DIR}/logs/run_$(date +%Y%m%d_%H%M%S).log"
REPORT_FILE="${PROJECT_DIR}/logs/report_$(date +%Y%m%d).md"
EMAIL_RECIPIENT="jacksbot@jacksbox.de"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create logs directory
mkdir -p "${PROJECT_DIR}/logs"

# Start logging
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=============================================="
echo "🏠 PRJ010 Property Search - $(date)"
echo "=============================================="

cd "$PROJECT_DIR"

# Track stats
NEW_COUNT=0
UPDATED_COUNT=0
ERRORS=""

# Step 1: Git pull
echo ""
echo "${YELLOW}[1/5] Pulling latest changes...${NC}"
git pull origin main || echo "Warning: git pull failed, continuing with local"

# Step 2: Run scraper
echo ""
echo "${YELLOW}[2/5] Running property scraper...${NC}"
if python3 scripts/scraper.py 2>&1; then
    echo "${GREEN}✓ Scraper completed successfully${NC}"
else
    ERRORS="${ERRORS}Scraper had errors. "
    echo "${RED}⚠ Scraper had errors, continuing...${NC}"
fi

# Step 3: Run enrichment
echo ""
echo "${YELLOW}[3/5] Running enrichment pipeline...${NC}"
if python3 scripts/enrich.py 2>&1; then
    echo "${GREEN}✓ Enrichment completed successfully${NC}"
else
    ERRORS="${ERRORS}Enrichment had errors. "
    echo "${RED}⚠ Enrichment had errors, continuing...${NC}"
fi

# Step 4: Regenerate website
echo ""
echo "${YELLOW}[4/5] Regenerating website...${NC}"
if python3 update_html_v3.py 2>&1; then
    echo "${GREEN}✓ Website regenerated successfully${NC}"
else
    ERRORS="${ERRORS}Website generation had errors. "
    echo "${RED}⚠ Website generation had errors${NC}"
fi

# Step 5: Git commit and push
echo ""
echo "${YELLOW}[5/5] Committing and pushing changes...${NC}"

# Check if there are changes
if git diff --quiet && git diff --staged --quiet; then
    echo "No changes to commit"
else
    # Count changes
    NEW_COUNT=$(git diff --name-only data/ | wc -l | tr -d ' ')
    
    # Stage and commit
    git add data/ docs/ report/
    COMMIT_MSG="🏠 Auto-update: $(date +%Y-%m-%d) | ${NEW_COUNT} files changed"
    git commit -m "$COMMIT_MSG" || true
    
    # Push to GitHub
    if git push origin main 2>&1; then
        echo "${GREEN}✓ Changes pushed to GitHub${NC}"
        echo "${GREEN}✓ GitHub Pages will rebuild automatically${NC}"
    else
        ERRORS="${ERRORS}Git push failed. "
        echo "${RED}⚠ Git push failed${NC}"
    fi
fi

# Generate report
echo ""
echo "=============================================="
echo "📊 Run Summary"
echo "=============================================="

cat > "$REPORT_FILE" << EOF
# Property Search Report - $(date +%Y-%m-%d)

## Summary
- **Run Time:** $(date)
- **Status:** $([ -z "$ERRORS" ] && echo "✅ Success" || echo "⚠️ Completed with warnings")
- **Files Changed:** ${NEW_COUNT}

## Listings by City
EOF

# Count listings per city
for city in freiburg augsburg leipzig halle magdeburg; do
    if [ -f "data/${city}/candidates_enriched.json" ]; then
        count=$(python3 -c "import json; print(len(json.load(open('data/${city}/candidates_enriched.json'))['candidates']))" 2>/dev/null || echo "?")
        echo "- **${city^}:** ${count} candidates" >> "$REPORT_FILE"
    fi
done

# Add errors if any
if [ -n "$ERRORS" ]; then
    echo "" >> "$REPORT_FILE"
    echo "## Warnings" >> "$REPORT_FILE"
    echo "$ERRORS" >> "$REPORT_FILE"
fi

# Display report
cat "$REPORT_FILE"

echo ""
echo "${GREEN}=============================================="
echo "✓ Property search completed at $(date)"
echo "Log: ${LOG_FILE}"
echo "Report: ${REPORT_FILE}"
echo "==============================================${NC}"

# Exit with appropriate code
[ -z "$ERRORS" ] && exit 0 || exit 1
