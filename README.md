### Content Hub 🚀

Content Hub is an automated, self-hosted content generation and scheduling pipeline. It autonomously sources trending or specified images from multiple web platforms, dynamically converts them into high-quality vertical or horizontal video formats, and handles automated cross-platform scheduling and publishing. 

### 🌟 Features

### 1. Multi-Platform Sourcing

Scrapes, authenticates, and extracts high-resolution images, metadata, and captions from: 

* **Reddit:** Sourced via PRAW (hot/top posts from specified subreddits).
* **Tumblr:** Filtered by tags and blogs using the Tumblr API.
* **Twitter (X):** Sourced from bookmarked links, user timelines, or search queries.
* **Pinterest:** Extracted from boards and user pins.

### 2. Automated Video Engine

* Converts static imagery into engaging, short-form video files.
* Supports automatic padding, zoom pan effects (Ken Burns), and resolution matching for vertical channels (9:16) or widescreen channels (16:9).
* Overlay engines add automated voiceovers (TTS), background tracks, subtitles, and text branding.

### 3. Cross-Platform Scheduling

Queue, manage, and dispatch your generated videos automatically to: 

* **YouTube Shorts & Longform**
* **Facebook Reels & Posts**
* **Instagram Reels**
* **TikTok**

### 🛠️ Architecture Overview

[ Sources ] ──────────> [ Media Processing ] ──────────> [ Publishing Hub ]
 ├─ Reddit               ├─ Image Optimization            ├─ YouTube API
 ├─ Tumblr               ├─ FFmpeg Video Engine           ├─ Meta Graph API (FB/IG)
 ├─ Twitter (X)          ├─ Text-To-Speech                └─ TikTok Content API
 └─ Pinterest            └─ Subtitle Generator

### 🚀 Quick Start

### Prerequisites

* Python 3.10+ or Node.js 18+ (depending on your stack implementation)
* **FFmpeg** installed on your system path
* API Developer Accounts for all target platforms

### Installation

1. Clone the repository: 

bash

git clone https://github.com/yourusername/content-hub.git
cd content-hub

Use code with caution.
2. Install system-level dependencies (Example for Ubuntu/Debian): 

bash

sudo apt update && sudo apt install ffmpeg -y

Use code with caution.
3. Install project dependencies: 

bash

pip install -r requirements.txt
# OR: npm install

Use code with caution.

### Configuration

Create a .env file in the root directory and populate your API credentials: 

env

# SOURCING CREDENTIALS
REDDIT_CLIENT_ID=your_reddit_id
REDDIT_CLIENT_SECRET=your_reddit_secret
TUMBLR_CONSUMER_KEY=your_tumblr_key
TWITTER_BEARER_TOKEN=your_x_token

# PUBLISHING CREDENTIALS
YOUTUBE_API_KEY=your_youtube_key
META_ACCESS_TOKEN=your_facebook_instagram_token
TIKTOK_ACCESS_TOKEN=your_tiktok_token

# ENGINE CONFIG
VIDEO_DEFAULT_DURATION=15
OUTPUT_FORMAT=mp4

Use code with caution.

### Running the App

Execute the main orchestrator to start parsing sources, rendering videos, and filling the publishing queues: 

bash

python main.py --run-pipeline

Use code with caution.

### 🗓️ How Schedulers Work

Content Hub uses a centralized database (SQLite/PostgreSQL) to handle the video pipeline logic. 

1. **Ingest Stage:** System fetches new assets hourly and stores them in a raw cache folder.
2. **Process Stage:** Images match target template configurations and compile into .mp4 video binaries.
3. **Queue Stage:** System calculates local posting windows based on historical performance metrics.
4. **Publish Stage:** Background workers periodically push ready assets via platform-specific REST endpoints.

### 🤝 Contributing

Contributions make the open-source community an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**. 

1. Fork the Project
2. Create your Feature Branch (git checkout -b feature/AmazingFeature)
3. Commit your Changes (git commit -m 'Add some AmazingFeature')
4. Push to the Branch (git checkout -b feature/AmazingFeature)
5. Open a Pull Request

### 📝 License

Distributed under the MIT License. See LICENSE for more information.
