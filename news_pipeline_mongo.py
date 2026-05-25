# news_pipeline_mongo.py
import os
import json
import time
import re
import gc
import sys
from datetime import datetime
from typing import List, Optional
from dotenv import load_dotenv
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

from serpapi import GoogleSearch
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from pymongo import MongoClient

# =====================
# CONFIG
# =====================
load_dotenv()

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = "NewsletterDB"
MONGO_COLLECTION = "news"

TOPIC_TOKEN_BUSINESS = "CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB"

HEADLINE_LIMIT = int(os.getenv("HEADLINE_LIMIT", "10"))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
SUPPORTING_PER_HEADLINE = int(os.getenv("SUPPORTING_PER_HEADLINE", "3"))
SCRAPE_WAIT = int(os.getenv("SCRAPE_WAIT", "3"))
BAD_LABELS = {"top news", "posts on x", "frequently asked questions"}

# =====================
# UTIL
# =====================
def safe_filename(s: str, maxlen: int = 80) -> str:
    f = re.sub(r'[^A-Za-z0-9_\- ]+', '', s)
    f = f.strip().replace(" ", "_")
    return f[:maxlen] if len(f) > 0 else "untitled"

# =====================
# SerpAPI headline fetcher
# =====================
def fetch_headlines_serpapi(topic_token: str, limit: int = 10):
    params = {
        "engine": "google_news",
        "topic_token": topic_token,
        "hl": "en",
        "gl": "US",
        "api_key": SERPAPI_API_KEY
    }
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
    except Exception as e:
        print("❌ Error fetching headlines:", e)
        return []

    news_results = results.get("news_results", [])[:limit]
    out = []
    for n in news_results:
        hl = n.get("highlight", {}) or {}
        title = (hl.get("title") or n.get("title") or "").strip()
        if not title or any(bad in title.lower() for bad in BAD_LABELS):
            continue
        link = hl.get("link") or n.get("link") or ""
        source = (hl.get("source") or {}).get("name") or (n.get("source") or {}).get("name") or ""
        date = hl.get("date") or n.get("date") or ""
        story_token = hl.get("story_token") or n.get("story_token")
        if not story_token:
            for s in (n.get("stories") or []):
                st = s.get("story_token")
                title_s = (s.get("title") or "").strip().lower()
                if st and title_s and not any(bad in title_s for bad in BAD_LABELS):
                    story_token = st
                    break
        out.append({
            "Title": title,
            "Link": link,
            "Source": source,
            "Published": date,
            "StoryToken": story_token or ""
        })
    return out

# =====================
# LLM helpers
# =====================
def strip_json_fence(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`").strip()
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
    return raw

def ask_gemini(prompt: str, system_instruction: str = "", json_mode: bool = False) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing from .env")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
        },
    }
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
    if json_mode:
        payload["generationConfig"]["response_mime_type"] = "application/json"

    resp = requests.post(
        url,
        params={"key": GEMINI_API_KEY},
        json=payload,
        timeout=120,
    )
    if not resp.ok:
        try:
            details = resp.json()
        except ValueError:
            details = resp.text
        raise RuntimeError(f"Gemini API error {resp.status_code}: {details}")
    data = resp.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Unexpected Gemini response: {data}") from exc

def ask_llm_select_top5(headlines: List[dict]) -> List[int]:
    prompt = "Here are 10 headlines. Choose 5 most interesting to a general reader. Answer ONLY a JSON object like {\"selected\": [1,2,3,4,5]} with indices (1-based).\n\n"
    for i, h in enumerate(headlines, start=1):
        prompt += f"{i}. {h['Title']}\n"

    raw = ask_gemini(
        prompt,
        system_instruction="You are an assistant that selects the most interesting news headlines.",
        json_mode=True,
    )
    print("LLM prompt:\n", prompt)
    raw = strip_json_fence(raw)
    try:
        sel = json.loads(raw).get("selected", [])
        return [int(x) for x in sel][:5]
    except:
        return list(range(1, min(6, len(headlines)+1)))

def ask_llm_summarize_two_langs(text: str) -> dict:
    prompt = (
        "Ringkas teks berikut dalam 2 bahasa (komprehensif, jelas, agak panjang).\n"
        "Output HARUS valid JSON exactly like:\n"
        '{ "id": "Ringkasan Bahasa Indonesia", "en": "English summary" }\n\n'
        "Teks:\n" + text
    )
    raw = ask_gemini(
        prompt,
        system_instruction="You are an assistant that summarizes news articles into Indonesian and English.",
        json_mode=True,
    )
    raw = strip_json_fence(raw)
    try:
        j = json.loads(raw)
        return {"id": j.get("id", "").strip(), "en": j.get("en", "").strip()}
    except:
        return {"id": raw, "en": ""}

def ask_llm_igpost_from_text(summary_en: str) -> Optional[dict]:
    prompt = (
        "Given the following English summary, produce JSON: {\"title\": \"short title (<=10 words)\", \"ig_post\": \"IG post text (one slide)\"}\n\n"
        f"Summary:\n{summary_en}"
    )
    raw = ask_gemini(
        prompt,
        system_instruction="You are a social media copywriter.",
        json_mode=True,
    )
    raw = strip_json_fence(raw)
    try:
        j = json.loads(raw)
        return {"title": j.get("title","").strip(), "ig_post": j.get("ig_post","").strip()}
    except:
        return None

# =====================
# Scraper
# =====================
def make_selenium_driver(headless: bool = True):
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.chrome.options import Options
    from selenium import webdriver

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=9222")
    print("🌐 Starting Selenium Chrome driver...")
    driver = webdriver.Chrome(service=ChromeService(), options=chrome_options)
    print("🌐 Chrome driver started")
    return driver


def scrape_article_text(driver, url: str, wait_seconds: int = SCRAPE_WAIT) -> str:
    try:
        driver.get(url)
        time.sleep(wait_seconds)
        html = driver.page_source 
        soup = BeautifulSoup(html, "html.parser")
        article = soup.find("article") or soup.find(role="main")
        if article:
            paras = [p.get_text().strip() for p in article.find_all("p") if p.get_text().strip()]
            return "\n".join(paras)
        body = soup.body
        if body:
            paras = [p.get_text().strip() for p in body.find_all("p") if p.get_text().strip()]
            return "\n".join(paras)
        return ""
    except Exception as e:
        print("❌ Error loading URL:", url, e)
        return ""

# =====================
# FULL PIPELINE
# =====================
def run_full_pipeline():
    client_mongo = MongoClient(MONGO_URI)
    db = client_mongo[MONGO_DB]
    news_col = db[MONGO_COLLECTION]

    print("🔎 Fetching headlines...")
    headlines = fetch_headlines_serpapi(TOPIC_TOKEN_BUSINESS, limit=HEADLINE_LIMIT)
    if not headlines:
        print("No headlines -> exit")
        return

    print("🤖 Selecting top 5 headlines via LLM...")
    top_idx = ask_llm_select_top5(headlines[:HEADLINE_LIMIT])
    print("🤖 LLM returned top indices:", top_idx)
    selected = [headlines[i-1] for i in top_idx if 1 <= i <= len(headlines)]
    print("Selected:", [h["Title"] for h in selected])

    driver = make_selenium_driver(headless=True)

    for h in selected:
        title_safe = safe_filename(h["Title"], 60)
        print(f"\n📂 Processing headline: {h['Title']}")
        token = h.get("StoryToken")
        supporting_articles = []

        if token:
            params = {
                "engine": "google_news",
                "story_token": token,
                "hl": "en",
                "gl": "US",
                "api_key": SERPAPI_API_KEY
            }
            try:
                results = GoogleSearch(params).get_dict()
                news_results = results.get("news_results", [])[:SUPPORTING_PER_HEADLINE]
                links = [nr.get("link") for nr in news_results if nr.get("link")]
            except:
                links = []

            for link in links:
                print(f"   Scraping article: {link}")
                text = scrape_article_text(driver, link)
                print(f"   Done scraping, length={len(text)}")
                if text.strip():
                    supporting_articles.append({"link": link, "text": text})

        combined_text = "\n".join([a["text"] for a in supporting_articles])
        if len(combined_text) > 100000:
            combined_text = combined_text[:100000]
        summaries = ask_llm_summarize_two_langs(combined_text) if combined_text else {"id":"","en":""}
        ig_post = ask_llm_igpost_from_text(summaries.get("en","")) if summaries.get("en") else None

        doc = {
            "title": h.get("Title"),
            "link": h.get("Link"),
            "source": h.get("Source"),
            "published": h.get("Published"),
            "story_token": h.get("StoryToken"),
            "selected_top5": True,
            "supporting_articles": supporting_articles,
            "summaries": summaries,
            "ig_post": ig_post,
            "created_at": datetime.now()
        }
        print(f"💾 Inserting document for headline: {h['Title']}")
        news_col.insert_one(doc)
        print(f"✅ Inserted into MongoDB: {h['Title']}")

    driver.quit()
    print("\n🏁 Pipeline finished. All data saved in MongoDB collection:", MONGO_COLLECTION)
    gc.collect()

if __name__ == "__main__":
    run_full_pipeline()
