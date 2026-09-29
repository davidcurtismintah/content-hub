### Content Hub 🚀

OmniContent Pipeline is an automated, end-to-end media engine that sources images from multiple content networks, converts them into engaging videos, and schedules them for publishing across major video-sharing platforms. 

### 🌟 Features

* **Multi-Platform Scraping:** Automatically fetch trending or targeted images from **Reddit**, **Tumblr**, **Twitter (X)**, and **Pinterest**.
* **Dynamic Video Engine:** Convert static images into videos complete with modern transitions, customizable aspect ratios (e.g., 9:16 Shorts/Reels), and audio tracks.
* **Unified Publisher:** Automatically queue, manage, and schedule video uploads directly to **YouTube**, **Facebook**, **Instagram**, and **TikTok**.
* **Intelligent Automation:** Set up cron-based workflows or configuration triggers to keep your social media channels active 24/7 without manual intervention.

### 🛠️ Tech Stack & Dependencies

* **Core Pipeline:** Python 3.10+ / Node.js
* **Media Processing:** FFmpeg / MoviePy (for image-to-video rendering)
* **Scraping Frameworks:** PRAW (Reddit), Tweepy (X), Tumblr API, Playwright / BeautifulSoup (Pinterest)
* **API Distribution:** Google API Client (YouTube), Meta Graph API (Facebook/Instagram), TikTok Content Posting API

### 🚀 Getting Started

### Prerequisites

Ensure you have the following installed on your machine: 

* Python 3.10+ or Node.js LTS
* FFmpeg (must be added to your system's PATH)

### Installation

1. **Clone the repository:** 

bash

git clone https://github.com/yourusername/omnicontent-pipeline.git
cd omnicontent-pipeline

Use code with caution.
2. **Install dependencies:** 

bash

# If using Python
pip install -r requirements.txt

# If using Node.js
npm install

Use code with caution.

### Configuration

1. Copy the environment template file: 

bash

cp .env.example .env

Use code with caution.
2. Open .env and fill in your respective API keys, tokens, and credentials: 

env

# --- SOURCE CREDENTIALS ---
REDDIT_CLIENT_ID=your_reddit_id
REDDIT_CLIENT_SECRET=your_reddit_secret
TWITTER_X_BEARER_TOKEN=your_x_token
TUMBLR_CONSUMER_KEY=your_tumblr_key
PINTEREST_ACCESS_TOKEN=your_pinterest_token

# --- DESTINATION CREDENTIALS ---
YOUTUBE_API_KEY=your_youtube_key
META_ACCESS_TOKEN=your_facebook_instagram_token
TIKTOK_OPEN_API_KEY=your_tiktok_key

# --- PIPELINE SETTINGS ---
VIDEO_DURATION_SEC=15
ASPECT_RATIO=9_16
OUTPUT_DIR=./output

Use code with caution.

### 💻 Usage

### 1. Run the Entire Pipeline

Execute the main controller script to scrape, process, and schedule content in a single run: 

bash

python main.py --run-all

Use code with caution.

### 2. Run Modules Individually

If you want to control separate steps of your pipeline: 

* **Scrape Images Only:** 

bash

python main.py --source reddit --query "infographics" --limit 10

Use code with caution.
* **Convert Images to Videos:** 

bash

python main.py --process-media --input ./images --audio background.mp3

Use code with caution.
* **Schedule Uploads:** 

bash

python main.py --schedule --platforms youtube instagram tiktok

Use code with caution.

### 📅 Scheduling & Queue Management

The application features a built-in JSON/Database queue system. You can view, modify, or rearrange scheduled posts by editing the generated queue.json file or accessing the dashboard (if enabled). 

json

{
  "post_id": "001",
  "video_path": "./output/render_001.mp4",
  "title": "Amazing Art Spot!",
  "description": "#art #trending #shorts",
  "schedule_time": "2026-10-01T15:00:00Z",
  "status": "pending"
}

Use code with caution.

### 🤝 Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. 

1. Fork the Project
2. Create your Feature Branch (git checkout -b feature/AmazingFeature)
3. Commit your Changes (git commit -m 'Add some AmazingFeature')
4. Push to the Branch (git push origin feature/AmazingFeature)
5. Open a Pull Request

### 📄 License

Distributed under the MIT License. See LICENSE for more information.
