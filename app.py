from flask import Flask, render_template, redirect, url_for
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from threading import Thread
from datetime import datetime
import os
import traceback

# import pipeline function
from news_pipeline_mongo import run_full_pipeline
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = "NewsletterDB"
MONGO_COLLECTION = "news"

mongo_error = None
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    db = client[MONGO_DB]
    news_col = db[MONGO_COLLECTION]
except PyMongoError as exc:
    client = None
    db = None
    news_col = None
    mongo_error = str(exc)

# Global variable to track pipeline status
pipeline_status = {"running": False, "last_run": None, "error": None}

# Helper to run pipeline in background
def run_pipeline_background():
    global pipeline_status
    pipeline_status["running"] = True
    pipeline_status["error"] = None
    try:
        run_full_pipeline()
    except Exception as exc:
        pipeline_status["error"] = str(exc)
        traceback.print_exc()
    finally:
        pipeline_status["running"] = False
        pipeline_status["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@app.route("/")
def index():
    # Fetch latest news from MongoDB
    news = []
    global mongo_error
    if news_col is not None:
        try:
            news = list(news_col.find().sort("created_at", -1).limit(20))
            mongo_error = None
        except PyMongoError as exc:
            mongo_error = str(exc)
    return render_template("index.html", news=news, pipeline_status=pipeline_status, mongo_error=mongo_error)

@app.route("/run_pipeline")
def run_pipeline():
    if not pipeline_status["running"]:
        # Run pipeline in background
        thread = Thread(target=run_pipeline_background)
        thread.start()
    return redirect(url_for("index"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # default 5000 supaya sama dengan docker run
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

