import os
import sys
import json
import logging
import feedparser
import requests
from dotenv import load_dotenv
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
    """Fetch the transcript for a given video ID using yt-dlp."""
    import yt_dlp
    import webvtt
    import glob

    logger.info(f"Attempting to fetch transcript for {video_id} using yt-dlp...")
    
    # We will save the subtitle temporarily
    ydl_opts = {
        'skip_download': True,        # Don't download the video
        'writesubtitles': True,       # Write manual subtitles
        'writeautomaticsub': True,    # Write auto-generated subtitles if no manual ones
        'subtitleslangs': ['en'],     # English
        'outtmpl': f'{video_id}.%(ext)s', # Temporary filename
        'quiet': True,
        'no_warnings': True
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f'https://www.youtube.com/watch?v={video_id}'])
            
        # yt-dlp might save it as .en.vtt or similar depending on auto/manual
        # Let's find the generated vtt file
        vtt_files = glob.glob(f"{video_id}*.vtt")
        
        if not vtt_files:
            logger.warning(f"No English subtitles found for {video_id}.")
            return "" # Return empty string meaning "processed, but no subs exist"
            
        vtt_file = vtt_files[0]
        
        # Parse the VTT and extract plain text
        full_transcript = ""
        for caption in webvtt.read(vtt_file):
            # Clean up the text (remove newlines within the same caption frame)
            text_cleaned = caption.text.replace('\n', ' ').strip()
            # Avoid repeating exactly the same line immediately (common in auto-captions)
            if not full_transcript.endswith(text_cleaned + " "):
                full_transcript += text_cleaned + " "
                
        # Clean up the file
        for f in vtt_files:
             os.remove(f)
             
        return full_transcript.strip()
        
    except Exception as e:
        logger.error(f"Fatal error fetching transcript for {video_id}: {e}")
        # Clean up any partial files
        vtt_files = glob.glob(f"{video_id}*.vtt")
        for f in vtt_files:
             try: os.remove(f) 
             except: pass
        return None # Return None meaning "Error, need to retry next time"

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
            return False
        response.raise_for_status()
        logger.info("Successfully sent message to Telegram.")
        return True
    except Exception as e:
        logger.error(f"Error sending message to Telegram: {e}")
        return False

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
    
    if transcript is None:
        logger.error("Failed to fetch transcript due to an error. Will retry on next run.")
        return # Exit without saving to history

    if transcript != "":
        summary = generate_summary(transcript, title)
        
        if summary:
            message = f"🎬 <b>New Video Uploaded: {title}</b>\n🔗 <a href='{link}'>Watch here</a>\n\n<b>Summary:</b>\n{summary}"
            
            if len(message) > 4000:
                message = message[:4000] + "\n... [Summary Truncated]"
                
            success = send_telegram_message(message)
            
            if success:
                # ONLY mark as processed if sending the message worked
                history.append(video_id)
                save_history(history)
                logger.info(f"Processing complete for {video_id}.")
            else:
                logger.error("Failed to send Telegram message. Will retry on next run.")
        else:
            logger.error("Failed to generate summary. Will retry on next run.")
    else:
         # transcript is exactly ""
         logger.warning("No english transcript available (none created by author or YouTube). Marking as processed to skip in future.")
         history.append(video_id)
         save_history(history)

def main():
    logger.info("Starting YouTube Scraper Check via GitHub Actions...")
    
    # Run the job exactly once and exit
    job()

if __name__ == "__main__":
    main()
