# YouTube Automation & Summarizer Bot 🤖

This project is an automated Python script designed to monitor a specific YouTube channel, fetch its latest video transcripts, generate executive summaries using AI (via OpenRouter), and deliver those summaries directly to a Telegram chat.

It gives users a quick, actionable breakdown of high-value YouTube videos (specifically focusing on new Tech and AI tools) without having to watch the entire video.

## ✅ Features

1. **YouTube RSS Scraping**: Automatically detects new video uploads for a hardcoded YouTube Channel ID via `feedparser`.
2. **Transcript Fetching**: Extracts the exact dialogue from videos using `youtube-transcript-api`.
3. **AI Summarization**: Sends transcripts to an OpenRouter LLM relying on external instructions provided in `system_prompt.md`.
4. **Telegram Notifications**: Dispatches neatly structured, HTML-formatted summary messages containing the video title, link, AI technologies discussed, and future impact.
5. **State Management**: Uses `history.json` to track processed video IDs and prevent duplicate Telegram messages.

## 🚀 Setup & Installation

1. Copy `.env.example` to `.env` and fill in your API keys:
   - `OPENROUTER_API_KEY`: Your OpenRouter API Key.
   - `TELEGRAM_BOT_TOKEN`: Your Telegram Bot Token.
   - `TELEGRAM_CHAT_ID`: Your Telegram Chat ID.
   - `YOUTUBE_CHANNEL_ID`: The ID of the YouTube channel to monitor.

2. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the script:
   ```bash
   python main.py
   ```

## ☁️ Next Immediate Step: Cloud Deployment

The script currently depends on a local `schedule` loop to check for videos every day at 9 AM.
**The immediate next goal is to implement cloud deployment.**

- The target platform is **GitHub Cloud (GitHub Actions)** or standard cloud hosting.
- The objective is to configure a workflow/cron job so the script runs automatically in the cloud 24/7 without needing a personal computer to remain on.

## 🔮 Future Implementations: Bulk & Monthly Scraping

The current implementation relies on the YouTube XML RSS feed, which is hard-limited by YouTube to only show the last 15 uploaded videos.

To support archiving or processing an entire month's worth of videos for a specific creator, an alternative scraping method is required. **Please refer to the detailed proposals in [docs/1-bulk_scraping_ideas.md](docs/1-bulk_scraping_ideas.md) before implementing any bulk extraction features.** The recommended approach is transitioning from the RSS feed to utilizing the `scrapetube` library for deep channel traversal.
