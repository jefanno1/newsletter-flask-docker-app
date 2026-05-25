# LLM News Summarizer

An end-to-end news summarization pipeline and Flask dashboard. The project fetches current business news from Google News through SerpAPI, lets an LLM select the most interesting headlines, scrapes supporting articles, generates bilingual summaries, creates Instagram-ready post copy, and stores the final result in MongoDB Atlas.

The current web version uses Gemini as the LLM provider so the pipeline can run on a free-tier-friendly setup.

## Project Goals

- Automate the daily process of finding relevant news.
- Reduce manual reading by summarizing multiple supporting articles per headline.
- Produce output in both Indonesian and English.
- Generate short social media copy from the English summary.
- Store structured results in MongoDB so they can be displayed in a dashboard.
- Provide a simple web UI to run the pipeline and review the latest generated news items.

## Tech Stack

| Area | Technology |
| --- | --- |
| Backend web app | Flask |
| News source | Google News via SerpAPI |
| LLM | Gemini API, default model `gemini-2.5-flash` |
| Scraping | Selenium, Chrome, BeautifulSoup |
| Database | MongoDB Atlas or local MongoDB |
| Language | Python |
| Frontend | HTML/Jinja template |

## Main Folder Structure

```text
Scraping_New/
  README.md
  Newsletter_Web/
    app.py
    news_pipeline_mongo.py
    requirements.txt
    Dockerfile
    templates/
      index.html
      pipeline_status.html
    static/
      style.css
```

Older experimental scripts also exist in `Scraping_New/`, such as standalone query scripts and file-output pipeline versions. The actively used web app is inside `Newsletter_Web/`.

## Core Files

### `Newsletter_Web/app.py`

This is the Flask web application.

Responsibilities:

- Loads environment variables from `.env`.
- Connects to MongoDB.
- Displays the latest 20 news documents from the `NewsletterDB.news` collection.
- Provides a `/run_pipeline` route.
- Starts the pipeline in a background thread so the browser does not hang.
- Tracks pipeline status with:

```python
pipeline_status = {"running": False, "last_run": None, "error": None}
```

### `Newsletter_Web/news_pipeline_mongo.py`

This is the main pipeline.

Responsibilities:

- Fetches Google News headlines through SerpAPI.
- Uses Gemini to select the top 5 headlines.
- Fetches supporting links for each selected story.
- Scrapes each article with Selenium and BeautifulSoup.
- Combines article text for each headline.
- Uses Gemini to generate Indonesian and English summaries.
- Uses Gemini to generate Instagram post text.
- Inserts the final structured document into MongoDB.

### `Newsletter_Web/templates/index.html`

This is the dashboard page.

It shows:

- Pipeline status.
- A Run Pipeline link.
- Pipeline errors, if any.
- MongoDB connection errors, if any.
- Latest news items.
- Indonesian summary.
- English summary.
- Instagram title and post text.

## Environment Variables

Create a `.env` file inside `Newsletter_Web/`.

```env
SERPAPI_API_KEY=your_serpapi_key
GEMINI_API_KEY=your_gemini_key
MONGO_URI=your_mongodb_connection_string

# Optional
GEMINI_MODEL=gemini-2.5-flash
HEADLINE_LIMIT=10
SUPPORTING_PER_HEADLINE=3
SCRAPE_WAIT=3
PORT=5000
```

Important:

- Do not commit `.env`.
- `MONGO_URI` can point to MongoDB Atlas or a local MongoDB instance.
- `SUPPORTING_PER_HEADLINE=3` is useful for demos because it keeps the pipeline faster.
- Increasing `SUPPORTING_PER_HEADLINE` improves context quality but makes scraping slower.

## How To Run Locally

From PowerShell:

```powershell
cd "D:\zephaniah_I\Project LLM\Project LLM News\Scraping_serpapi\Scraping_New\Newsletter_Web"
pip install -r requirements.txt
python app.py
```

Open:

```text
http://localhost:5000
```

Then click:

```text
Run Pipeline
```

## Pipeline Flow

```text
User clicks Run Pipeline
        |
        v
Flask route /run_pipeline starts background thread
        |
        v
Fetch 10 business headlines from Google News via SerpAPI
        |
        v
Gemini selects the top 5 most interesting headlines
        |
        v
For each selected headline:
  - Use story_token to fetch supporting article links
  - Scrape article text with Selenium and BeautifulSoup
  - Combine scraped text
  - Ask Gemini for Indonesian and English summaries
  - Ask Gemini for Instagram-ready post text
  - Insert result into MongoDB
        |
        v
Dashboard reads latest documents from MongoDB
```

## MongoDB Document Shape

Each generated news item is stored in MongoDB with a structure similar to this:

```json
{
  "title": "News headline",
  "link": "https://source-url.example/article",
  "source": "Source name",
  "published": "Published date from Google News",
  "story_token": "Google News story token",
  "selected_top5": true,
  "supporting_articles": [
    {
      "link": "https://supporting-source.example/article",
      "text": "Scraped article text"
    }
  ],
  "summaries": {
    "id": "Ringkasan Bahasa Indonesia",
    "en": "English summary"
  },
  "ig_post": {
    "title": "Short social title",
    "ig_post": "Instagram post text"
  },
  "created_at": "datetime"
}
```

## Routes

| Route | Method | Purpose |
| --- | --- | --- |
| `/` | GET | Shows the dashboard and latest MongoDB news items |
| `/run_pipeline` | GET | Starts the pipeline in a background thread, then redirects to `/` |

## Why Gemini Replaced OpenAI

The original version used OpenAI for headline selection, summarization, and social post generation. During testing, the OpenAI API key hit quota limits. The pipeline was updated to use Gemini through the REST API:

```text
https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
```

This keeps the same project architecture while allowing the demo to run with a different LLM provider.

## Error Handling

The web app now surfaces failures instead of silently failing.

Examples:

- If MongoDB cannot connect, the dashboard displays a MongoDB error.
- If the pipeline fails, the dashboard displays a pipeline error.
- If Gemini returns an API error, the dashboard shows the status code and response details.
- If the LLM returns invalid JSON, the code falls back where possible.

## Known Limitations

- The pipeline uses a single global in-memory status object, so it is designed for one local user/demo session rather than many concurrent users.
- `/run_pipeline` is a GET route. A production version should use POST.
- Selenium scraping can be slow because each article page must load in Chrome.
- Some publishers block scraping, have paywalls, or render content differently.
- The app stores full scraped article text in MongoDB, which is useful for debugging but may become large over time.
- There is no authentication on the dashboard yet.

## Possible Improvements

- Add a job queue such as Celery or RQ instead of a raw thread.
- Add user authentication.
- Add a progress table showing which headline is currently being processed.
- Add duplicate detection to avoid inserting the same headline repeatedly.
- Add source quality scoring.
- Add retry and backoff for SerpAPI, Gemini, and MongoDB calls.
- Add a POST endpoint for running the pipeline.
- Add pagination and search in the dashboard.
- Store only cleaned article snippets instead of full scraped text.
- Add tests for the LLM JSON parsing and MongoDB document creation.

## Interview Summary

This project demonstrates:

- API integration with SerpAPI and Gemini.
- Browser automation and scraping with Selenium.
- HTML parsing with BeautifulSoup.
- Background processing in a Flask app.
- Document database usage with MongoDB.
- LLM orchestration for selection, summarization, and content generation.
- Practical error handling and environment-based configuration.

