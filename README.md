

# `README.md`

<div align="center">

<img src="https://raw.githubusercontent.com/Compromisee/Mangadeck/main/docs/assets/banner.png" alt="Mangadeck" width="100%"/>

# Mangadeck

**Multi-source manga, manhwa, and manhua downloader**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/Compromisee/Mangadeck?style=flat-square&color=yellow)](https://github.com/Compromisee/Mangadeck/stargazers)
[![GitHub Issues](https://img.shields.io/github/issues/Compromisee/Mangadeck?style=flat-square&color=red)](https://github.com/Compromisee/Mangadeck/issues)
[![Discord](https://img.shields.io/badge/Discord-Join-5865F2?style=flat-square&logo=discord&logoColor=white)](https://discord.gg/u5jAS7Vt)
[![Website](https://img.shields.io/badge/Website-compromisee.github.io%2FMangadeck-4a8fe7?style=flat-square)](https://compromisee.github.io/Mangadeck)

---

**[Website](https://compromisee.github.io/Mangadeck)** &nbsp;·&nbsp;
**[Discord](https://discord.gg/u5jAS7Vt)** &nbsp;·&nbsp;
**[Reddit](https://www.reddit.com/user/Defiant_Chef8080/)** &nbsp;·&nbsp;
**[YouTube](https://www.youtube.com/@Whyshould1laugh)**

</div>

---

## What is Mangadeck?

Mangadeck is an open-source, multi-source manga downloader that queries **7 sites simultaneously**, automatically fills in missing chapters from secondary sources, and exports to **EPUB, CBZ, PDF, or organized image folders**.

If MangaDex only has One Piece up to chapter 763, Mangadeck finds chapters 764 through 1076 from Manganato, MangaKakalot, or MangaKatana — automatically — and gives you a complete, gap-free download.

It comes with three interfaces:

- **Web dashboard** — full-featured browser UI at `localhost:5000`
- **Terminal UI** — rich, animated terminal interface with live progress bars
- **Desktop GUI** — minimal Tkinter window for quick use
- **REST API** — headless server mode for scripting and integrations

---

## Table of Contents

- [Features](#features)
- [Screenshots](#screenshots)
- [Supported Sources](#supported-sources)
- [Output Formats](#output-formats)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Web Dashboard](#web-dashboard)
  - [Terminal UI](#terminal-ui)
  - [Desktop GUI](#desktop-gui)
  - [CLI Mode](#cli-mode)
  - [Headless API Server](#headless-api-server)
- [Configuration](#configuration)
- [REST API Reference](#rest-api-reference)
- [How Aggregation Works](#how-aggregation-works)
- [EPUB Compatibility](#epub-compatibility)
- [Auto-Crop System](#auto-crop-system)
- [Notifications](#notifications)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [Community](#community)
- [License](#license)

---

## Features

### Multi-API Aggregation Engine

Mangadeck does not rely on a single source. It queries all enabled APIs in parallel, merges results by title similarity, and when a primary source is missing chapters, it searches every other source to fill the gaps.

- Queries up to 7 sources simultaneously using `ThreadPoolExecutor`
- Title similarity matching with `SequenceMatcher` (threshold: 72%)
- Three-phase gap filling: known source IDs → search-based fill → targeted gap fill
- Source attribution tracking: every chapter is tagged with its source
- Cached source IDs per title to avoid redundant searches
- Works for long-running series: tested with One Piece (1076 chapters), Naruto, Bleach, Tower of God

### Download Modes

- **Download all** — every available chapter from all aggregated sources
- **Chapter range** — `1-50`, `1,3,5`, `1-10,20-30`, any combination
- **Volume range** — `1-5`, converted internally to chapter lists
- **Interactive browser** — checkbox chapter or volume selection in the web UI
- **Cart system** — add multiple manga, configure formats per-item, download all at once
- **Priority queue** — sequential processing with configurable delays between items

### Output Formats

| Format | Details |
|--------|---------|
| EPUB | EPUB 3.0 fixed-layout, Apple Books compatible, proper reading direction, NCX + nav.xhtml |
| CBZ | ComicInfo.xml metadata, ZIP archive, works with all comic readers |
| PDF | Auto-sized pages via Pillow, universal compatibility |
| Images | Organized `Chapter_XXXX/page_XXXX.jpg` folder structure |

### Three Interfaces

| Interface | Technology | Best for |
|-----------|------------|---------|
| Web Dashboard | Flask + vanilla JS | Most users, full feature access |
| Terminal UI | Rich + pyfiglet | Server usage, SSH, power users |
| Desktop GUI | Tkinter | Quick desktop use, minimal setup |

### Smart Image Processing

- Auto-detect and remove white/black borders using corner sampling
- Configurable threshold (default: 10) and minimum crop ratio (default: 70%)
- Row/column scanning with configurable step size for performance
- JPEG quality control (default: 92) and WebP support
- Prevents over-cropping: skips crop if result would be less than `min_ratio` of original

### Manga / Manhwa / Manhua Support

- Auto-detects content type from source language and genre tags
- Right-to-left reading direction for manga
- Vertical scrolling for manhwa and manhua
- EPUB embeds correct `page-progression-direction` in spine
- Long-strip / webtoon mode with no over/under cropping

### Notifications

- Desktop push notifications (macOS, Linux, Windows)
- Discord webhook integration with embeds
- Telegram bot messages with Markdown formatting
- Triggered on single download completion or full queue completion
- Test buttons in dashboard settings

### REST API and Headless Mode

- Full REST API with JSON responses
- Server-Sent Events for live download progress
- Cover image proxy to avoid CORS issues
- Config import/export via API
- Can be integrated into any external tool, script, or automation system

---

## Screenshots

> Web dashboard, terminal UI, and desktop GUI screenshots

```
Web Dashboard  →  http://127.0.0.1:5000
Terminal UI    →  python main.py --mode tui
Desktop GUI    →  python main.py --mode gui
```

---

## Supported Sources

| Source | Type | Supports | Notes |
|--------|------|----------|-------|
| MangaDex | REST API | Manga, Manhwa, Manhua | 50+ languages, official API |
| Manganato / Chapmanganato | Scraper | Manga, Manhwa, Manhua | Large catalog, fast |
| MangaKakalot | Scraper | Manga, Manhwa, Manhua | Good for long series |
| MangaKatana | Scraper | Manga, Manhwa, Manhua | Broad coverage |
| MangaHere / Fanfox | Scraper | Manga, Manhwa, Manhua | Volume metadata available |
| ManhuaPlus | Scraper | Manhua only | Chinese comics specialist |
| LINE Webtoon | Scraper | Manhwa only | Official Webtoon platform |

All sources are queried in parallel. Results are deduplicated and merged by title similarity.

---

## Output Formats

### EPUB

Apple Books, Google Play Books, Kobo, Moon+ Reader, Kindle (with conversion).

- EPUB 3.0 specification
- Fixed-layout with `pre-paginated` rendition
- `META-INF/com.apple.ibooks.display-options.xml` for Apple Books
- Correct `page-progression-direction` in spine (`rtl` / `ltr`)
- Vertical mode for manhwa/manhua long strips
- Auto-generated cover page from first chapter image
- Chapter-based NCX and nav.xhtml navigation

### CBZ

Komga, Kavita, Calibre, CDisplayEx, YACReader, Panels, Chunky, Mango.

- Standard ZIP archive with image files
- `ComicInfo.xml` with title, language, manga flag, reading direction
- Chapter-organized folder structure inside archive

### PDF

Any PDF viewer: Preview, Adobe Acrobat, browsers, e-readers.

- Images rendered at 150 DPI equivalent
- Pages auto-sized to source image dimensions
- Generated via Pillow

### Images

For custom workflows, Plex manga plugins, or any image viewer.

```
MangaTitle/
  Chapter_0001/
    page_0001.jpg
    page_0002.jpg
    ...
  Chapter_0002/
    ...
```

---

## Installation

### Requirements

| Requirement | Version |
|-------------|---------|
| Python | 3.9 or higher |
| pip | Latest recommended |

### Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| flask | ≥3.0.0 | Web dashboard and REST API |
| requests | ≥2.31.0 | HTTP client for all sources |
| beautifulsoup4 | ≥4.12.0 | HTML parsing for scrapers |
| Pillow | ≥10.0.0 | Image processing, PDF, auto-crop |
| rich | ≥13.0.0 | Terminal UI |
| pyfiglet | ≥1.0.2 | Terminal UI title art |

### Install

```bash
# Clone
git clone https://github.com/Compromisee/Mangadeck.git
cd Mangadeck

# Install dependencies
pip install -r requirements.txt
```

### Optional: Virtual environment (recommended)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

---

## Quick Start

```bash
# Start the web dashboard
python main.py

# Dashboard is at http://127.0.0.1:5000
```

1. Open `http://127.0.0.1:5000` in your browser
2. Go to **Search** and type a manga title
3. Click a result to open the detail panel
4. Set format, chapter range (optional), and click **Download**
5. Watch live progress in the **Downloads** tab

---

## Usage

### Web Dashboard

```bash
python main.py
# or explicitly
python main.py --mode web --port 5000 --host 127.0.0.1
```

Available at `http://127.0.0.1:5000`.

**Tabs:**

| Tab | Description |
|-----|-------------|
| Home | Hero section, trending manga, quick search |
| Discover | Trending from all sources, language filter |
| Search | Full-text search with source filter |
| Downloads | Live progress, speed, ETA, cancel |
| Cart | Add multiple manga, bulk download |
| Queue | Sequential processing, start/stop |
| Sources | API status, availability checker |
| Logs | Filterable log viewer with stats |
| Settings | Full configuration panel |

**Chapter selection in the modal:**

- Type `1-50` in the **Chapters** field to download chapters 1 through 50
- Type `1-5` in the **Volumes** field to download by volume
- Use the **browse** toggle to visually check individual chapters or volumes
- Leave both blank to download everything

### Terminal UI

```bash
python main.py --mode tui
```

Full-color terminal dashboard with pyfiglet gradient title, animated progress bars, interactive menus.

**Menu options:**

| Key | Action |
|-----|--------|
| 1 | Interactive manga search |
| 2 | Browse trending |
| 3 | View active downloads with live bars |
| 4 | Manage download cart |
| 5 | Manage queue |
| 6 | Source availability |
| 7 | Settings editor |
| 8 | Log viewer |
| 9 | Quick download (search + immediate start) |
| 0 | Exit |

**Search flow:**

```
>> 1
  Search: One Piece
  Language [en]: en

  Found 5 results:
  [1] One Piece (mangadex, manganato) - ongoing - 1076 chapters
  [2] One Piece Colored (mangadex) - ongoing - 1076 chapters
  ...

  Actions: [d]ownload [c]art [i]nfo [b]ack
  Action: d
  Select # (e.g. 1 or 1,3,5): 1
  Format [cbz]: epub
  Chapters (e.g. 1-50, blank=all): 1-100

  [Download] Starting: One Piece
  Download started. View with option [3].
```

### Desktop GUI

```bash
python main.py --mode gui
```

Minimal Tkinter window with dark theme.

**Tabs:**

- **Search** — query, results treeview, format selector, chapter/volume range inputs
- **Downloads** — treeview with status, progress percentage, speed, ETA
- **Cart** — list of queued manga, bulk download button
- **Settings** — scrollable settings panel with all configuration options
- **Logs** — scrolled text area with colored log levels

### CLI Mode

```bash
# Search
python main.py --mode cli --search "Berserk"

# Download all chapters
python main.py --mode cli --download "mdx_801513ba" --format epub

# Download chapter range
python main.py --mode cli --download "mdx_801513ba" --format cbz --chapters 1-100

# Download specific chapters
python main.py --mode cli --download "mdx_801513ba" --chapters "1,5,10,50-60"

# Download by volume
python main.py --mode cli --download "mdx_801513ba" --volumes 1-10 --format epub

# Different language
python main.py --mode cli --download "mdx_801513ba" --language fr --format cbz

# Custom output directory
python main.py --mode cli --download "mdx_801513ba" --output /home/user/manga

# Override reading direction
python main.py --mode cli --download "mdx_801513ba" --reading-direction rtl
```

**All CLI arguments:**

| Argument | Default | Description |
|----------|---------|-------------|
| `--mode` | `web` | `web`, `gui`, `tui`, `headless`, `cli` |
| `--port` | `5000` | Server port |
| `--host` | `127.0.0.1` | Server host (use `0.0.0.0` for network access) |
| `--search` | — | Search query (CLI mode) |
| `--download` | — | Manga ID to download |
| `--format` | config | `epub`, `cbz`, `pdf`, `images` |
| `--chapters` | all | Chapter range: `1-50`, `1,3,5`, `1-10,20-30` |
| `--volumes` | all | Volume range: `1-10` |
| `--language` | `en` | Language code |
| `--output` | `~/Mangadeck` | Output directory |
| `--reading-direction` | auto | `rtl`, `ltr`, `vertical` |
| `--config` | `~/.mangadeck/config.json` | Config file path |

### Headless API Server

```bash
# Start API-only server (no browser UI)
python main.py --mode headless --port 5000 --host 0.0.0.0
```

Exposes the full REST API without serving the dashboard HTML. Useful for running Mangadeck on a server and controlling it from external tools.

---

## Configuration

Config is stored at `~/.mangadeck/config.json` and is created automatically on first run.

### All Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `output_dir` | `~/Mangadeck` | Download output directory |
| `default_format` | `cbz` | Default output format |
| `language` | `en` | Default language code |
| `reading_direction` | `auto` | `auto`, `rtl`, `ltr`, `vertical` |
| `max_concurrent_downloads` | `4` | Parallel manga download tasks |
| `max_concurrent_images` | `8` | Parallel image downloads per chapter |
| `max_api_workers` | `4` | Parallel API query threads |
| `bandwidth_limit_kbps` | `0` | Bandwidth cap in KB/s (0 = unlimited) |
| `rate_limit_delay` | `null` | Override per-source rate limit delay |
| `enabled_apis` | all | List of enabled source names |
| `auto_crop` | `true` | Enable automatic border cropping |
| `crop_threshold` | `10` | Color difference threshold for border detection |
| `crop_min_ratio` | `0.70` | Minimum size ratio after crop (prevents over-cropping) |
| `crop_padding` | `2` | Pixels to add back after crop |
| `jpeg_quality` | `92` | JPEG save quality (50–100) |
| `webp_quality` | `85` | WebP save quality |
| `epub_apple_books_compat` | `true` | Add Apple Books display options metadata |
| `epub_generate_cover` | `true` | Auto-generate cover page |
| `epub_vertical_mode` | `false` | Vertical scroll layout (manhwa/manhua) |
| `epub_page_width` | `800` | Fixed page width in pixels |
| `epub_page_height` | `1200` | Fixed page height in pixels |
| `pdf_page_size` | `auto` | PDF page size |
| `pdf_margin` | `0` | PDF page margin in pixels |
| `cbz_compression` | `0` | CBZ compression level (0 = store) |
| `notify_on_complete` | `false` | Enable completion notifications |
| `notify_desktop` | `false` | Desktop push notifications |
| `discord_webhook_url` | `""` | Discord webhook URL |
| `telegram_bot_token` | `""` | Telegram bot token |
| `telegram_chat_id` | `""` | Telegram chat ID |
| `auto_start_queue` | `false` | Start queue processing immediately when cart is downloaded |
| `queue_delay_seconds` | `2` | Seconds between queue items |
| `retry_failed` | `true` | Retry failed downloads |
| `max_retries` | `3` | Maximum retry attempts per image |
| `theme` | `dark` | Dashboard theme: `dark`, `light` |
| `high_contrast` | `false` | High contrast mode |
| `minimal_mode` | `false` | Minimal UI mode |
| `log_level` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `log_max_entries` | `5000` | Maximum in-memory log entries |
| `server_host` | `127.0.0.1` | Default server host |
| `server_port` | `5000` | Default server port |

### Edit config via API

```bash
# Get all settings
curl http://127.0.0.1:5000/api/config

# Update settings
curl -X POST http://127.0.0.1:5000/api/config \
  -H "Content-Type: application/json" \
  -d '{"default_format": "epub", "auto_crop": true}'

# Export config to file
curl http://127.0.0.1:5000/api/config/export -o config.json

# Import config from file
curl -X POST http://127.0.0.1:5000/api/config/import \
  -H "Content-Type: application/json" \
  --data-binary @config.json

# Reset single setting to default
curl -X POST "http://127.0.0.1:5000/api/config/reset?key=default_format"

# Reset all settings to defaults
curl -X POST http://127.0.0.1:5000/api/config/reset
```

---

## REST API Reference

Base URL: `http://127.0.0.1:5000` (configurable)

All responses are JSON.

### Search

```http
GET /api/search?q={query}&lang={lang}&page={page}&sources={sources}
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `q` | required | Search query |
| `lang` | `en` | Language code |
| `page` | `1` | Page number |
| `sources` | all | Comma-separated source names |

**Response:**
```json
{
  "results": [
    {
      "id": "mdx_a1c7c817",
      "title": "One Piece",
      "type": "manga",
      "status": "ongoing",
      "cover_url": "https://...",
      "source": "mangadex",
      "sources": ["mangadex", "manganato"],
      "source_ids": {"mangadex": "a1c7c817", "manganato": "manga-op123"},
      "chapter_count": 1076,
      "reading_direction": "rtl",
      "genres": ["Action", "Adventure", "Fantasy"],
      "authors": ["Oda Eiichiro"]
    }
  ],
  "count": 5,
  "page": 1,
  "language": "en"
}
```

### Trending

```http
GET /api/trending?lang={lang}&page={page}
```

Returns trending/popular manga from all sources.

### Manga Details

```http
GET /api/manga/{manga_id}?source={source}
```

Returns full metadata including chapter list.

### Chapters (Aggregated)

```http
GET /api/manga/{manga_id}/chapters?lang={lang}&aggregate={bool}&title={title}&source_ids={json}
```

When `aggregate=true` and `title` is provided, queries all sources to build a complete chapter list.

**Response includes `source_map`:** how many chapters came from each source.

### Volumes (Aggregated)

```http
GET /api/manga/{manga_id}/volumes?lang={lang}&title={title}&source_ids={json}
```

Returns chapters grouped by volume number.

### Download

```http
POST /api/download
Content-Type: application/json

{
  "manga_id": "mdx_a1c7c817",
  "title": "One Piece",
  "source": "mangadex",
  "source_ids": {"mangadex": "a1c7c817", "manganato": "manga-op123"},
  "format": "epub",
  "chapter_range": [1, 2, 3, 4, 5],
  "volume_range": null,
  "language": "en",
  "reading_direction": "rtl"
}
```

Returns `{"task_id": "task_000001", "status": "started"}`.

### Download Status

```http
GET /api/download/{task_id}
GET /api/downloads
POST /api/download/{task_id}/cancel
POST /api/downloads/clear
```

### Cart

```http
GET    /api/cart
POST   /api/cart/add
DELETE /api/cart/{item_id}
POST   /api/cart/clear
```

### Queue

```http
GET  /api/queue
POST /api/queue/start   {"enqueue_cart": true}
POST /api/queue/stop
DELETE /api/queue/{item_id}
POST /api/queue/clear
GET  /api/queue/history
```

### Sources

```http
GET  /api/sources
GET  /api/sources/check
POST /api/sources/enable   {"apis": ["mangadex", "manganato"]}
```

### Logs

```http
GET  /api/logs?level={level}&category={cat}&search={text}&limit={n}&offset={n}
POST /api/logs/clear
```

### Live Events (SSE)

```http
GET /api/events
```

Returns a `text/event-stream` with live download and queue status. Connect with:

```javascript
const sse = new EventSource("/api/events");
sse.onmessage = (e) => {
  const { tasks, queue } = JSON.parse(e.data);
};
```

### System

```http
GET /api/system
```

Returns version, paths, and aggregate stats.

### Cover Proxy

```http
GET /api/proxy/image?url={encoded_url}
```

Proxies cover images from source sites to avoid CORS issues.

### Notifications

```http
POST /api/notifications/test
Content-Type: application/json

{"channel": "discord", "webhook_url": "https://discord.com/api/webhooks/..."}
{"channel": "telegram", "bot_token": "...", "chat_id": "..."}
{"channel": "desktop"}
{"channel": "all"}
```

---

## How Aggregation Works

Mangadeck uses a three-phase approach to build complete chapter lists:

### Phase 1 — Known Sources

If a manga has been searched before, Mangadeck caches the source IDs found across all APIs (stored in `_title_source_cache`). All cached sources are queried in parallel to immediately gather chapters from every known location.

```
mangadex:    chapters 1-763
manganato:   chapters 1-1076
mangakakalot: chapters 1-1055
```

### Phase 2 — Search-Based Fill

For any enabled source not yet in the known ID cache, Mangadeck searches by title and finds the best title match (similarity > 55%). It then fetches the full chapter list from that source.

This handles the case where the user has never searched on a particular source before. Every enabled API gets a chance to contribute chapters.

### Phase 3 — Gap Detection

After phases 1 and 2, Mangadeck looks at the chapter number sequence. If there are integer gaps (e.g. chapters 50-60 are missing), and the gap count is less than 50% of total chapters (to avoid false positives), it tries each remaining source one more time specifically to fill those gaps.

### Deduplication

When multiple sources have the same chapter number, Mangadeck keeps the first one found (from the highest-priority source: MangaDex > Manganato > MangaKakalot > MangaKatana > MangaHere > ManhuaPlus > Webtoon).

### Source Priority

```
mangadex      → best metadata, 50+ languages, official API
manganato     → large catalog, fast scraper
mangakakalot  → good for older/longer series
mangakatana   → broad coverage
mangahere     → volume metadata available
manhuaplus    → manhua specialist
webtoon       → official Webtoon platform
```

---

## EPUB Compatibility

Mangadeck generates EPUB files that work correctly in Apple Books, Google Play Books, Kobo, Moon+ Reader, and standard EPUB readers.

### Fixed-Layout

Each page is a separate XHTML document with `pre-paginated` rendition. This tells readers to display one image per screen without reflowing text.

### Apple Books

`META-INF/com.apple.ibooks.display-options.xml` is included:

```xml
<display_options>
  <platform name="*">
    <option name="fixed-layout">true</option>
    <option name="open-to-spread">false</option>
    <option name="orientation-lock">portrait</option>
  </platform>
</display_options>
```

### Reading Direction

The `page-progression-direction` attribute in the OPF spine is set correctly:

- `rtl` for Japanese manga
- `ltr` for manhwa and manhua

### Navigation

Both NCX (EPUB 2 compatibility) and nav.xhtml (EPUB 3) are generated with chapter-level navigation points.

---

## Auto-Crop System

The cropper removes uniform white or black borders from manga pages.

### How It Works

1. **Border color sampling** — samples 4 corner regions to determine the predominant border color (R, G, B average)
2. **Row scanning** — scans from top and bottom inward. A row is considered border if ≥95% of sampled pixels match the border color within threshold
3. **Column scanning** — same process from left and right
4. **Bounding box** — combines row/column results to get content boundaries
5. **Minimum ratio check** — if the cropped area would be less than `crop_min_ratio` (default 70%) of the original in either dimension, the crop is skipped entirely
6. **Padding** — adds `crop_padding` pixels back on each side (default 2px)
7. **Save** — saves at configured JPEG quality

### Configuration

| Setting | Default | Effect |
|---------|---------|--------|
| `auto_crop` | `true` | Enable/disable entirely |
| `crop_threshold` | `10` | Color tolerance (higher = more aggressive) |
| `crop_min_ratio` | `0.70` | Below this ratio, skip the crop |
| `crop_padding` | `2` | Padding pixels added after crop |

---

## Notifications

### Discord

1. Create a webhook in your Discord server channel settings
2. Copy the webhook URL
3. Paste it in Mangadeck settings under **Discord webhook URL**
4. Click **Test** to verify
5. Enable **Notifications** toggle

Notifications include an embed with title, message, color-coded by type (green = complete, red = error, blue = info).

### Telegram

1. Create a bot via [@BotFather](https://t.me/BotFather) on Telegram
2. Copy the bot token
3. Get your chat ID by messaging your bot and calling `https://api.telegram.org/bot{token}/getUpdates`
4. Enter both in Mangadeck settings
5. Click **Test**

### Desktop

- **macOS** — uses `osascript` native notification
- **Linux** — uses `notify-send` (requires libnotify)
- **Windows** — uses PowerShell toast notifications, or `plyer` if installed

---

## Project Structure

```
mangadeck/
│
├── main.py                         Entry point, CLI, mode launcher
├── requirements.txt                Python dependencies
├── run.py                          Quick launcher with auto-detect
├── run.sh                          Unix launcher
├── run.bat                         Windows launcher
├── Makefile                        Development shortcuts
├── setup.py                        Package setup
├── LICENSE                         MIT License
├── README.md                       This file
│
├── api/
│   ├── __init__.py
│   ├── base.py                     Abstract base API class
│   ├── mangadex.py                 MangaDex REST API adapter
│   ├── mangakatana.py              MangaKatana scraper
│   ├── manganato.py                Manganato / Chapmanganato scraper
│   ├── mangahere.py                MangaHere / Fanfox scraper
│   ├── mangakakalot.py             MangaKakalot scraper
│   ├── webtoon.py                  LINE Webtoon scraper
│   ├── manhuaplus.py               ManhuaPlus scraper
│   └── aggregator.py               Multi-source aggregation engine
│
├── core/
│   ├── __init__.py
│   ├── config.py                   Thread-safe config with file persistence
│   ├── logger.py                   In-memory log buffer + file logging
│   ├── downloader.py               Multi-threaded download engine
│   ├── converter.py                EPUB / CBZ / PDF / Images converter
│   ├── cropper.py                  Auto-crop with minimum ratio protection
│   ├── metadata.py                 Cover generation and metadata builder
│   ├── queue_manager.py            Cart and queue management system
│   └── notifier.py                 Desktop / Discord / Telegram notifications
│
├── gui/
│   ├── __init__.py
│   └── GUI.py                      Tkinter desktop GUI
│
├── tui/
│   ├── __init__.py
│   └── TUI.py                      Rich terminal UI with pyfiglet
│
├── web/
│   ├── __init__.py
│   ├── server.py                   Flask server + REST API + SSE
│   ├── templates/
│   │   └── dash.html               Dashboard HTML
│   └── static/
│       ├── css/
│       │   └── style.css           Dashboard CSS (dark/light themes)
│       └── js/
│           └── app.js              Dashboard JavaScript
│
├── docs/                           GitHub Pages promotional site
│   ├── index.html
│   ├── style.css
│   └── script.js
│
└── .github/
    └── workflows/
        └── pages.yml               GitHub Actions deployment
```

---

## Contributing

Contributions are welcome. Please open an issue before making large changes.

### Getting Started

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/Mangadeck.git
cd Mangadeck

# Create a branch
git checkout -b feature/your-feature-name

# Set up environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Verify everything compiles
make lint

# Test source availability
make test-sources
```

### Adding a New Source

1. Create `api/your_source.py` inheriting from `BaseAPI`
2. Implement `search()`, `get_manga_details()`, `get_chapters()`, `get_chapter_images()`
3. Set `SOURCE_NAME`, `BASE_URL`, `RATE_LIMIT`, `SUPPORTS_*` class variables
4. Register in `api/aggregator.py` `__init__` dict and priority list
5. Add a prefix entry to `PREFIX_MAP` if the source has a unique ID prefix

### Submitting a PR

- Keep changes focused and small
- Add a clear description of what changed and why
- Test with at least one full manga download
- Make sure `make lint` passes (all files compile without errors)

### Reporting Issues

Open a GitHub issue with:

- Manga title and source
- Exact error message from the **Logs** tab
- Your OS and Python version
- Steps to reproduce

---

## Community

| Platform | Link |
|----------|------|
| Discord | [discord.gg/u5jAS7Vt](https://discord.gg/u5jAS7Vt) |
| Reddit | [u/Defiant_Chef8080](https://www.reddit.com/user/Defiant_Chef8080/) |
| YouTube | [@Whyshould1laugh](https://www.youtube.com/@Whyshould1laugh) |
| GitHub | [github.com/Compromisee](https://github.com/Compromisee) |
| Website | [compromisee.github.io/Mangadeck](https://compromisee.github.io/Mangadeck) |

---

## License

MIT License. See [LICENSE](LICENSE) for full text.

```
MIT License

Copyright (c) 2024 Compromisee

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

<div align="center">

Made by [Compromisee](https://github.com/Compromisee)

[⬆ Back to top](#mangadeck)

</div>
