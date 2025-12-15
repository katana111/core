# AI News Analyzer Setup

The parsersvc enrichment service now includes AI-powered analysis of press mentions using free LLM models via OpenRouter.

## Features

- **Automatic Sentiment Analysis**: Determines if news is positive, negative, neutral, or mixed
- **Sentiment Scoring**: Provides a score from -1.0 (very negative) to 1.0 (very positive)
- **Key Topics Extraction**: Identifies main themes (funding, product launch, partnership, etc.)
- **Summary Generation**: Creates concise 2-3 sentence summaries
- **Detailed Analysis**: Provides business context and implications

## Setup (Optional - Free)

### Option 1: Use OpenRouter API (Recommended - Free Tier Available)

1. Sign up at https://openrouter.ai/
2. Get your free API key
3. Add to your environment:

```bash
export OPENROUTER_API_KEY="your_api_key_here"
```

Or add to your `.env` file:
```
OPENROUTER_API_KEY=your_api_key_here
```

**Model Used**: `meta-llama/llama-3.2-3b-instruct:free`
- Free tier available
- Good quality for news analysis
- Fast response times

### Option 2: Fallback Mode (No API Key)

If no API key is provided, the system automatically falls back to rule-based analysis:
- Basic sentiment detection using keyword matching
- Simple topic extraction
- No external API calls required

## Usage

The AI analysis runs automatically when press mentions are found:

```python
from services.parsersvc.enrichment_service import CompetitorEnrichmentService
from database import get_db

db = get_db()
db.initialize()

# Create service (AI analysis enabled by default)
service = CompetitorEnrichmentService(headless=True)

# Run enrichment - press mentions will be analyzed automatically
results = service.enrich_all_competitors()
```

## Database Schema

Press mentions with AI analysis are saved to `competitors_news` table:

| Field | Type | Description |
|-------|------|-------------|
| id | BIGINT | Auto-increment primary key |
| competitor_id | BIGINT | Foreign key to competitors |
| title | VARCHAR(500) | Article title/headline |
| url | TEXT | Article URL (if available) |
| source | VARCHAR(255) | Source (e.g., "parsers.vc") |
| published_date | DATE | Publication date |
| content | TEXT | Article content/excerpt |
| **summary** | TEXT | AI-generated summary |
| **sentiment** | VARCHAR(50) | positive/negative/neutral/mixed |
| **sentiment_score** | DECIMAL(3,2) | Score from -1.0 to 1.0 |
| **key_topics** | JSON | Array of identified topics |
| **analysis** | TEXT | AI-generated business analysis |
| created_at | TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | Last update time |

## Example Output

```sql
SELECT title, sentiment, sentiment_score, key_topics, summary 
FROM competitors_news 
WHERE competitor_id = 5
LIMIT 1;
```

```
Title: SEON Raises $94M Series B for Fraud Prevention Platform
Sentiment: positive
Sentiment Score: 0.85
Key Topics: ["funding", "product", "growth", "expansion"]
Summary: SEON has successfully raised $94 million in Series B funding to expand its fraud prevention platform. The funding will be used to enhance their AI-powered solution and expand into new markets. This represents significant investor confidence in their technology and market position.
```

## Querying News Data

### Get all positive news for a competitor:
```sql
SELECT title, sentiment_score, published_date, summary
FROM competitors_news
WHERE competitor_id = 5 AND sentiment = 'positive'
ORDER BY published_date DESC;
```

### Get recent news with high sentiment:
```sql
SELECT c.name, cn.title, cn.sentiment, cn.sentiment_score
FROM competitors_news cn
JOIN competitors c ON c.id = cn.competitor_id
WHERE cn.published_date >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
  AND ABS(cn.sentiment_score) > 0.7
ORDER BY cn.published_date DESC;
```

### Analyze competitor sentiment trends:
```sql
SELECT 
    c.name,
    COUNT(*) as total_mentions,
    AVG(cn.sentiment_score) as avg_sentiment,
    SUM(CASE WHEN cn.sentiment = 'positive' THEN 1 ELSE 0 END) as positive_count,
    SUM(CASE WHEN cn.sentiment = 'negative' THEN 1 ELSE 0 END) as negative_count
FROM competitors_news cn
JOIN competitors c ON c.id = cn.competitor_id
GROUP BY c.id, c.name
ORDER BY avg_sentiment DESC;
```

## Cost

- **With OpenRouter API**: Free tier available (rate limited)
- **Fallback Mode**: Completely free, no external dependencies

## Troubleshooting

### API Key Not Working
```bash
# Check if key is set
echo $OPENROUTER_API_KEY

# Test the key
curl https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer $OPENROUTER_API_KEY"
```

### Fallback to Rule-Based Analysis
If you see this message, the system is using fallback mode:
```
Warning: OPENROUTER_API_KEY not set. Get free key at https://openrouter.ai/
```

This is fine - the system will still work with basic sentiment analysis.

## Alternative Free AI APIs

You can modify `services/ai/news_analyzer.py` to use other free APIs:

1. **Hugging Face Inference API** (free tier)
2. **Together AI** (free tier available)
3. **Replicate** (pay-as-you-go, first requests free)

The current implementation uses OpenRouter for ease of use and model variety.
