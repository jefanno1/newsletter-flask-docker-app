# Newsletter Flask & Docker App
[![Ask DeepWiki](https://devin.ai/assets/askdeepwiki.png)](https://deepwiki.com/jefanno1/newsletter-flask-docker-app)

This repository contains a Flask web application that automates a news aggregation and summarization pipeline. The application fetches the latest business news, uses AI to select the most relevant articles, scrapes their content, generates summaries in both English and Indonesian, creates a draft for an Instagram post, and stores the results in a MongoDB database. The entire application is containerized with Docker for easy deployment and portability.

## Features

-   **Automated News Fetching**: Retrieves top business news headlines using the SerpAPI Google News API.
-   **AI-Powered Curation**: Utilizes an OpenAI model to select the 5 most interesting headlines from a fetched list.
-   **Web Scraping**: Employs Selenium with a headless Chrome browser to scrape the full text of supporting articles for each selected headline.
-   **Dual-Language Summarization**: Generates comprehensive summaries of the article content in both English and Indonesian using an OpenAI model.
-   **Social Media Content Generation**: Creates a short title and a draft for an Instagram post based on the English summary.
-   **Web Dashboard**: A simple Flask-based UI to view the processed news items and manually trigger the pipeline.
-   **Database Storage**: Persists all generated content, including headlines, summaries, and social media drafts, into a MongoDB collection.
-   **Dockerized Environment**: Fully containerized with a `Dockerfile` that handles all system and Python dependencies, including Google Chrome and ChromeDriver.

## Tech Stack

-   **Backend**: Flask
-   **Database**: MongoDB
-   **News API**: SerpAPI
-   **AI / LLM**: OpenAI
-   **Web Scraping**: Selenium, BeautifulSoup4
-   **Containerization**: Docker
-   **Languages**: Python, HTML

## Getting Started

### Prerequisites

-   [Docker](https://www.docker.com/get-started) installed and running.
-   [Git](https://git-scm.com/) for cloning the repository.
-   API keys for [SerpAPI](https://serpapi.com/) and [OpenAI](https://openai.com/).
-   A MongoDB instance (local or cloud-based like MongoDB Atlas) and its connection URI.

### Setup and Configuration

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/jefanno1/newsletter-flask-docker-app.git
    cd newsletter-flask-docker-app
    ```

2.  **Create an environment file:**

    Create a file named `.env` in the root of the project and add your credentials.

    ```env
    # .env
    MONGO_URI="mongodb://user:password@host:port"
    SERPAPI_API_KEY="YOUR_SERPAPI_API_KEY"
    OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
    ```

### Running with Docker (Recommended)

1.  **Build the Docker image:**
    This command builds the image using the `Dockerfile`, which installs all necessary dependencies including Google Chrome for Selenium.
    ```bash
    docker build -t newsletter-app .
    ```

2.  **Run the Docker container:**
    This command starts the application. It maps port 5000 on your local machine to port 5000 in the container and passes the environment variables from your `.env` file.
    ```bash
    docker run --rm -p 5000:5000 --env-file .env newsletter-app
    ```
    
    > **Note:** The `--rm` flag automatically removes the container when it exits.

3.  **Access the application:**
    Open your web browser and navigate to `http://localhost:5000`.

## Pipeline Workflow

The core logic resides in `news_pipeline_mongo.py` and is triggered via the `/run_pipeline` endpoint in the Flask app.

1.  **Fetch Headlines**: The pipeline starts by calling `fetch_headlines_serpapi` to get the top 10 business headlines from Google News.
2.  **Select Top 5**: These 10 headlines are sent to an OpenAI model via `ask_llm_select_top5`, which returns the indices of the 5 most interesting stories.
3.  **Process Each Story**: For each of the 5 selected headlines:
    a. **Find Supporting Articles**: Uses the `story_token` to find related articles via SerpAPI, ensuring a diversity of sources.
    b. **Scrape Content**: The `scrape_article_text` function uses a headless Selenium browser to visit each supporting article's URL and extract its main text content.
    c. **Summarize**: The combined text from all supporting articles is sent to the `ask_llm_summarize_two_langs` function. This produces a comprehensive summary in both Indonesian and English.
    d. **Create IG Post**: The English summary is used by `ask_llm_igpost_from_text` to generate a short, catchy title and a body text suitable for an Instagram post.
4.  **Store in MongoDB**: The complete data package—including the original headline, summaries, IG post content, and supporting article links—is inserted as a single document into the `news` collection in your MongoDB database.
5.  **Display Results**: The main page of the web app queries the MongoDB collection to display the latest processed news items in reverse chronological order.
