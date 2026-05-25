# Interview Presentation Guide

Use this guide as your speaking notes when presenting the LLM News Summarizer project.

## 30-Second Pitch

This project is an automated news summarizer. It pulls business headlines from Google News using SerpAPI, uses Gemini to choose the most interesting stories, scrapes supporting articles, summarizes them in Indonesian and English, creates Instagram-ready content, stores everything in MongoDB, and displays the latest results in a Flask dashboard.

The main idea is to turn a manual content workflow into an automated pipeline: discover news, gather context, summarize, generate social copy, and publish results to a dashboard.

## Problem Statement

Manually creating daily news content takes time because a person has to:

- Search for trending headlines.
- Decide which headlines are worth covering.
- Open multiple supporting articles.
- Read and combine the information.
- Write summaries in more than one language.
- Create social media captions.
- Save and organize the output.

This project automates that workflow.

## Solution Overview

The application has two parts:

- A Flask dashboard for triggering the pipeline and viewing results.
- A Python pipeline that handles news fetching, scraping, LLM processing, and MongoDB storage.

When the user clicks `Run Pipeline`, Flask starts the pipeline in a background thread. The dashboard remains responsive while the pipeline works in the background.

## Architecture

```text
Browser
  |
  v
Flask Dashboard
  |
  |-- reads latest results from MongoDB
  |
  |-- starts background thread
        |
        v
      News Pipeline
        |
        |-- SerpAPI / Google News
        |-- Gemini API
        |-- Selenium + BeautifulSoup
        |-- MongoDB Atlas
```

## Main Components

### 1. Flask Web App

File:

```text
Newsletter_Web/app.py
```

What it does:

- Starts the web server.
- Connects to MongoDB.
- Renders the dashboard.
- Starts the pipeline when `/run_pipeline` is called.
- Tracks running status, last run time, and errors.

Key design decision:

The pipeline runs in a background thread because scraping and LLM calls can take several minutes. If the pipeline ran directly inside the request, the browser request could time out or feel frozen.

### 2. Pipeline

File:

```text
Newsletter_Web/news_pipeline_mongo.py
```

What it does:

1. Fetches headlines from Google News using SerpAPI.
2. Uses Gemini to choose the top 5 headlines.
3. Uses Google News `story_token` to fetch supporting article links.
4. Scrapes article text with Selenium and BeautifulSoup.
5. Combines text from supporting articles.
6. Uses Gemini to produce Indonesian and English summaries.
7. Uses Gemini to create Instagram post text.
8. Saves the final document to MongoDB.

### 3. Dashboard Template

File:

```text
Newsletter_Web/templates/index.html
```

What it shows:

- Pipeline status.
- Last run time.
- Pipeline errors.
- MongoDB errors.
- Latest 20 news documents.
- Summaries and IG post output.

### 4. Database

Database:

```text
NewsletterDB
```

Collection:

```text
news
```

MongoDB stores the pipeline output as flexible documents. This is useful because each article can have a variable number of supporting links and nested generated content.

## Demo Script

Use this flow in an interview.

### Step 1: Open The Dashboard

Open:

```text
http://localhost:5000
```

Say:

The dashboard reads the latest generated news items from MongoDB. It also shows the pipeline status, so I can see whether a run is idle, running, or failed.

### Step 2: Show The Run Pipeline Button

Say:

This button starts the complete automation pipeline. In production I would make this a POST route or a scheduled background job, but for a demo a simple button makes the workflow easy to show.

### Step 3: Click Run Pipeline

Say:

Once clicked, Flask starts a background thread. The server remains responsive while the pipeline fetches headlines, calls Gemini, scrapes articles, and inserts results into MongoDB.

### Step 4: Refresh The Dashboard

Say:

After the pipeline inserts documents, the dashboard displays the generated summaries and social media content. This proves the data is flowing from external APIs, through the processing pipeline, into MongoDB, and back to the UI.

### Step 5: Show Code

Recommended files to show:

- `app.py`: web routes, MongoDB connection, background thread.
- `news_pipeline_mongo.py`: pipeline orchestration and Gemini calls.
- `index.html`: rendering the stored results.

## Key Technical Talking Points

### API Integration

SerpAPI is used because Google News does not provide a simple official public API for this workflow. SerpAPI returns structured headline data, including a `story_token` that can be used to retrieve related articles.

### LLM Usage

Gemini is used for three separate tasks:

- Ranking headlines by interest.
- Summarizing scraped article text in Indonesian and English.
- Turning the English summary into short Instagram-ready copy.

The code asks Gemini for JSON output so the pipeline can parse the result and store it consistently.

### Scraping

Selenium loads the article pages because many news sites render content dynamically. BeautifulSoup then parses the loaded HTML and extracts paragraphs from either an `<article>` tag, a `role="main"` element, or the page body as a fallback.

### Storage

MongoDB is a good fit because the final document is naturally nested:

- headline metadata
- supporting articles
- bilingual summaries
- social media content
- timestamp

### Error Visibility

The dashboard shows errors from MongoDB and the pipeline. This is important because background tasks can otherwise fail silently.

## Important Code Decisions

### Why Background Thread?

The pipeline includes network calls, browser scraping, and LLM requests. Running it in the request thread would block the browser. A background thread allows the request to return immediately.

For production, I would replace the thread with a job queue such as Celery, RQ, or a cloud task system.

### Why Environment Variables?

API keys and database credentials should not be hardcoded. The app loads secrets from `.env`, which is ignored by Git.

### Why Gemini REST Instead Of SDK?

Using REST keeps the dependency list smaller and makes it clear how the model endpoint is called. It also made it easy to swap from OpenAI to Gemini without changing the rest of the pipeline.

### Why MongoDB?

MongoDB handles nested JSON-like data naturally. Each generated news item contains arrays and nested fields, so document storage is simpler than designing multiple relational tables for this prototype.

## Current Limitations

Be honest about these in the interview. It shows maturity.

- The pipeline is built for a demo/local workflow, not high-concurrency production usage.
- `/run_pipeline` uses GET. It should be POST in production.
- The in-memory `pipeline_status` resets when the server restarts.
- Selenium scraping is slower than API-based content ingestion.
- Some sites block scraping or have paywalls.
- There is no authentication yet.
- There is no deduplication yet, so repeated runs can insert similar stories.
- Full article text is stored in MongoDB, which can grow quickly.

## Production Improvements

If asked how you would improve it:

- Replace background threads with Celery, RQ, or cloud queues.
- Add a scheduled daily run.
- Add user login.
- Add deduplication using headline hash, canonical URL, or story token.
- Add progress tracking per headline.
- Add retry logic with exponential backoff.
- Add structured logging.
- Add tests for API parsing, JSON extraction, and MongoDB inserts.
- Add a cleaner UI with filters, search, and pagination.
- Add monitoring for API quota usage.
- Store summarized article chunks instead of full raw text.

## Likely Interview Questions And Answers

### Why did you use an LLM here?

The LLM is useful because the task is not just extraction. It needs judgment and language generation: choosing interesting headlines, combining information from multiple articles, summarizing in two languages, and writing social media copy.

### Why not summarize only the original headline link?

One article can be incomplete or biased. By scraping supporting articles from the same Google News story cluster, the summary has more context and can be more balanced.

### What happens if Gemini returns invalid JSON?

The code strips Markdown code fences and tries to parse JSON. If parsing fails in some functions, it falls back to a safe default, such as selecting the first five headlines or returning raw text.

### What was a real bug you solved?

The first version failed silently when the pipeline crashed in a background thread. I added error tracking to `pipeline_status` so the dashboard shows pipeline errors. I also fixed Windows console encoding problems by forcing UTF-8 output for logs.

### Why did you move from OpenAI to Gemini?

The project originally used OpenAI, but the API key hit quota limits during testing. I abstracted the LLM calls and switched the provider to Gemini while keeping the rest of the pipeline architecture unchanged. That shows the pipeline is provider-flexible.

### How do you know it worked?

A successful run inserted new MongoDB documents with:

- title
- supporting article text
- Indonesian summary
- English summary
- IG title
- IG post text
- created timestamp

The dashboard then displayed those documents.

## One-Minute Closing Summary

This project shows an end-to-end AI automation workflow: external data ingestion, LLM ranking, web scraping, bilingual summarization, social content generation, database persistence, and a dashboard for users. It is currently a prototype, but the architecture is clear and extendable. The next step would be making the background processing production-grade with a queue, adding deduplication, and improving the dashboard UX.

