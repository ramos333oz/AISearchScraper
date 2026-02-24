# YouTube Automation & Summarizer Bot

I find that videos from AISearch youtube channel are very helpful, but due to time constraint, I find I struggle to complete every each of his newly uploaded video, so I created this bot specifically just to scrape the information from his newly uploaded videos, uses LLM to summarize it then send it to Telegram.

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

## ☁️ Cloud Deployment: GitHub Actions

The script is currently hosted and automated via **GitHub Actions**. This allows the bot to run 24/7 without requiring a local computer to remain on.

- **Schedule**: The workflow is configured to run automatically every day at **09:00 UTC**.
- **State Persistence**: The bot automatically commits updates to `history.json` back to the repository after each run, ensuring it tracks processed videos across sessions.
- **Manual Trigger**: The script can be triggered manually via the **Actions** tab in the GitHub repository.

To set up your own deployment:

1. Push the code to a private GitHub repository.
2. Configure **Repository Secrets** for
   `OPENROUTER_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and `YOUTUBE_CHANNEL_ID`.
3. Ensure **Workflow permissions** are set to "Read and write permissions" in Settings -> Actions -> General.

## 🔮 Future Implementations: Bulk & Monthly Scraping

The current implementation relies on the YouTube XML RSS feed, which is hard-limited by YouTube to only show the last 15 uploaded videos.

To support archiving or processing an entire month's worth of videos for a specific creator, an alternative scraping method is required. **Please refer to the detailed proposals in [docs/1-bulk_scraping_ideas.md](docs/1-bulk_scraping_ideas.md) before implementing any bulk extraction features.** The recommended approach is transitioning from the RSS feed to utilizing the `scrapetube` library for deep channel traversal.
