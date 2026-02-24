import os
import sys
import json
import logging
import feedparser
import requests
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID")

# File to store processed video IDs
HISTORY_FILE = "history.json"

if not all([OPENROUTER_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, YOUTUBE_CHANNEL_ID]):
    logger.error("Missing one or more required environment variables in .env file.")
    logger.error("Please ensure OPENROUTER_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, and YOUTUBE_CHANNEL_ID are set.")
    sys.exit(1)

# Initialize OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

def load_history():
    """Load previously processed video IDs."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning(f"Error reading {HISTORY_FILE}. Starting fresh.")
            return []
    return []

def save_history(history):
    """Save processed video IDs."""
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)

def get_latest_video(channel_id):
    """Fetch the latest video from the YouTube channel's RSS feed."""
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    feed = feedparser.parse(feed_url)
    
    if not feed.entries:
        logger.warning(f"No videos found for channel ID: {channel_id}")
        return None

    latest_entry = feed.entries[0]
    video_id = latest_entry.yt_videoid
    title = latest_entry.title
    link = latest_entry.link
    
    return {
        'id': video_id,
        'title': title,
        'link': link
    }

def get_video_transcript(video_id):
    """Fetch the transcript for a given video ID."""
    from youtube_transcript_api.formatters import TextFormatter
    try:
        # Based on the documentation for the latest versions
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id)
        
        # Format as plain text (no timestamps)
        formatter = TextFormatter()
        full_transcript = formatter.format_transcript(transcript)
        
        return full_transcript
    except Exception as e:
        logger.error(f"Could not fetch transcript for {video_id}: {e}")
        return None

def generate_summary(transcript, video_title):
    """Use OpenRouter LLM to generate a summary of the transcript."""
    logger.info("Generating summary via OpenRouter...")
    
    # Read the system prompt from the external configuration file
    try:
        with open("system_prompt.md", "r", encoding="utf-8") as f:
            system_prompt = f.read()
    except FileNotFoundError:
        logger.error("system_prompt.md not found. Generating default text.")
        system_prompt = "You are a helpful assistant."

    user_prompt = f"""
    Please summarize the following YouTube video transcript according to the requested HTML format.
    Video Title: {video_title}
    
    Transcript:
    {transcript[:15000]}
    """

    try:
        response = client.chat.completions.create(
            # Using a fast and capable default model
            model="google/gemini-3-flash-preview", 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        return None

def send_telegram_message(text):
    """Send a message to the configured Telegram chat."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"  # Switched to HTML as Markdown requires strict escaping in Telegram
    }
    
    try:
        response = requests.post(url, json=payload)
        if not response.ok:
            logger.error(f"Telegram API Error: {response.text}")
        response.raise_for_status()
        logger.info("Successfully sent message to Telegram.")
    except Exception as e:
        logger.error(f"Error sending message to Telegram: {e}")

def job():
    """Wrapper for the main scraping logic."""
    logger.info("Starting scheduled YouTube Scraper Check...")
    
    history = load_history()
    latest_video = get_latest_video(YOUTUBE_CHANNEL_ID)
    
    if not latest_video:
        logger.info("Could not fetch the latest video. Skipping this check.")
        return

    video_id = latest_video['id']
    title = latest_video['title']
    link = latest_video['link']
    
    logger.info(f"Latest video found: '{title}' ({video_id})")

    if video_id in history:
        logger.info(f"Video {video_id} has already been processed. Nothing to do.")
        return

    logger.info(f"New video detected! Fetching transcript for {video_id}...")
    transcript = get_video_transcript(video_id)
    
    if transcript:
        summary = generate_summary(transcript, title)
        
        if summary:
            # We use HTML tags since we changed parse_mode to HTML
            message = f"🎬 <b>New Video Uploaded: {title}</b>\n🔗 <a href='{link}'>Watch here</a>\n\n<b>Summary:</b>\n{summary}"
            
            # Telegram messages are limited to 4096 characters
            if len(message) > 4000:
                message = message[:4000] + "\n... [Summary Truncated]"
                
            send_telegram_message(message)
            
            # Mark as processed
            history.append(video_id)
            save_history(history)
            logger.info(f"Processing complete for {video_id}.")
        else:
            logger.error("Failed to generate summary.")
    else:
         logger.warning("No transcript available to summarize. We will still mark it as processed so we don't spam errors.")
         # Optional: You might want to skip adding to history if you want to retry later if captions get auto-generated
         history.append(video_id)
         save_history(history)

def main():
    logger.info("Starting YouTube Scraper Bot...")
    
    # Run once immediately on startup
    job()
    
    # Then schedule it to run periodically. 
    # For example: every 1 day. You can change this to `schedule.every().day.at("09:00").do(job)` if you want a specific time.
    import schedule
    import time
    
    schedule.every().day.at("09:00").do(job)
    logger.info("Scheduler initialized. Checking for new videos once a day at 9AM.")
    
    while True:
        schedule.run_pending()
        time.sleep(60) # check the scheduler every minute to save CPU

if __name__ == "__main__":
    main()
