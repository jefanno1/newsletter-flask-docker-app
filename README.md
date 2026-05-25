# LLM News Summarizer

A Flask web app that automates a news-content workflow:

1. Fetch business headlines from Google News through SerpAPI.
2. Use Gemini to select the most interesting headlines.
3. Scrape supporting articles with Selenium and BeautifulSoup.
4. Generate Indonesian and English summaries.
5. Generate Instagram-ready post copy.
6. Store the result in MongoDB.
7. Display the latest generated news items in a dashboard.

This repository is designed so another user can clone it, add their own API keys, and run it locally or with Docker.

## Features

- Google News headline discovery via SerpAPI.
- LLM headline selection using Gemini.
- Supporting article scraping with headless Chrome.
- Bilingual summaries: Indonesian and English.
- Instagram title and post generation.
- MongoDB persistence.
- Flask dashboard with pipeline status and visible error messages.
- Docker support for easier Selenium/Chrome setup.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Web app | Flask |
| News API | SerpAPI Google News API |
| LLM | Gemini API, default `gemini-2.5-flash` |
| Scraping | Selenium, Chrome, BeautifulSoup |
| Database | MongoDB Atlas or local MongoDB |
| Container | Docker, Docker Compose |

## Repository Structure

```text
.
├── app.py
├── news_pipeline_mongo.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .dockerignore
├── .gitignore
├── README.md
├── docs/
│   └── interview-presentation-guide.md
└── templates/
    └── index.html
```

## Requirements

You need API keys or services for:

- SerpAPI: https://serpapi.com/
- Gemini API: https://ai.google.dev/
- MongoDB: MongoDB Atlas or a local MongoDB server

For local non-Docker execution, you also need:

- Python 3.11 or newer
- Google Chrome installed
- ChromeDriver available to Selenium, or a Selenium version/environment that can locate a matching driver

Docker is recommended because the image installs Chrome and ChromeDriver for you.

## Environment Setup

Copy the example environment file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Edit `.env`:

```env
SERPAPI_API_KEY=your_serpapi_key_here
GEMINI_API_KEY=your_gemini_api_key_here
MONGO_URI=mongodb+srv://user:password@cluster.example.mongodb.net/

# Optional settings
GEMINI_MODEL=gemini-2.5-flash
HEADLINE_LIMIT=10
SUPPORTING_PER_HEADLINE=3
SCRAPE_WAIT=3
PORT=5000
```

Notes:

- `.env` is ignored by Git.
- Do not commit real API keys or database credentials.
- `SUPPORTING_PER_HEADLINE=3` is good for demos because it keeps the run faster.
- Increase `SUPPORTING_PER_HEADLINE` if you want richer summaries and do not mind longer scraping time.

## Run With Docker

Build and start the app:

```bash
docker compose up --build
```

Open:

```text
http://localhost:5000
```

Stop the app:

```bash
docker compose down
```

## Run Locally Without Docker

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
python app.py
```

Open:

```text
http://localhost:5000
```

## How To Use

1. Open the dashboard at `http://localhost:5000`.
2. Click `Run Pipeline`.
3. The dashboard will show `Running...`.
4. Wait for the pipeline to finish.
5. Refresh the page to see the latest generated news items.

The first run can take several minutes because Selenium loads and scrapes multiple article pages.

## Pipeline Workflow

```text
Dashboard /run_pipeline route
        |
        v
Start background thread
        |
        v
Fetch headlines from SerpAPI
        |
        v
Gemini selects top 5 headlines
        |
        v
For each selected headline:
  - Fetch supporting links with story_token
  - Scrape article text with Selenium
  - Parse paragraphs with BeautifulSoup
  - Summarize in Indonesian and English with Gemini
  - Generate Instagram content with Gemini
  - Insert final document into MongoDB
        |
        v
Dashboard displays latest MongoDB documents
```

## MongoDB Output Shape

Documents are inserted into:

```text
Database: NewsletterDB
Collection: news
```

Example document:

```json
{
  "title": "News headline",
  "link": "https://example.com/article",
  "source": "Publisher",
  "published": "Published date from Google News",
  "story_token": "Google News story token",
  "selected_top5": true,
  "supporting_articles": [
    {
      "link": "https://example.com/supporting-article",
      "text": "Scraped article text"
    }
  ],
  "summaries": {
    "id": "Ringkasan Bahasa Indonesia",
    "en": "English summary"
  },
  "ig_post": {
    "title": "Short title",
    "ig_post": "Instagram post text"
  },
  "created_at": "datetime"
}
```

## Routes

| Route | Method | Purpose |
| --- | --- | --- |
| `/` | GET | Show dashboard and latest news documents |
| `/run_pipeline` | GET | Start the pipeline in a background thread |

## Configuration Reference

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `SERPAPI_API_KEY` | Yes | None | SerpAPI key for Google News results |
| `GEMINI_API_KEY` | Yes | None | Gemini API key for LLM calls |
| `MONGO_URI` | Yes | `mongodb://localhost:27017` | MongoDB connection string |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | Gemini model name |
| `HEADLINE_LIMIT` | No | `10` | Number of headlines fetched before LLM selection |
| `SUPPORTING_PER_HEADLINE` | No | `3` | Number of supporting articles scraped per selected headline |
| `SCRAPE_WAIT` | No | `3` | Seconds to wait after loading each article page |
| `PORT` | No | `5000` | Flask server port |

## Error Handling

The dashboard displays:

- MongoDB connection errors.
- Pipeline errors.
- Gemini API errors.

This prevents background-thread failures from feeling like nothing happened.

## Known Limitations

- The pipeline status is stored in memory and resets when the app restarts.
- `/run_pipeline` uses GET for demo simplicity. A production app should use POST.
- Selenium scraping can be slow and some publishers may block scraping.
- Duplicate detection is not implemented yet.
- There is no authentication.
- The app stores full scraped article text, which can grow the database quickly.

## Future Improvements

- Use Celery, RQ, or another job queue instead of a raw thread.
- Add progress tracking per headline.
- Add deduplication by `story_token`, URL, or headline hash.
- Add user login.
- Add pagination and search.
- Add retries with exponential backoff.
- Add tests for LLM JSON parsing and MongoDB document creation.
- Store cleaned article snippets instead of full raw scraped text.

## Interview Notes

Presentation notes are available in:

```text
docs/interview-presentation-guide.md
```

