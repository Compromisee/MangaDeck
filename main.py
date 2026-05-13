#!/usr/bin/env python3
"""
Mangadeck - Multi-API Manga Downloader
https://github.com/Compromisee/Mangadeck
"""

import sys
import os
import argparse
import threading
import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import Config
from core.logger import Logger
from core.queue_manager import QueueManager
from core.downloader import DownloadEngine
from api.aggregator import Aggregator


VERSION = "1.0.0"
APP_NAME = "Mangadeck"


def main():
    parser = argparse.ArgumentParser(
        prog="mangadeck",
        description="Mangadeck - Multi-API Manga Downloader"
    )
    parser.add_argument(
        "--mode", choices=["gui", "tui", "web", "headless", "cli"],
        default="web",
        help="Launch mode"
    )
    parser.add_argument("--port", type=int, default=5000, help="Web server port")
    parser.add_argument("--host", default="127.0.0.1", help="Web server host")
    parser.add_argument("--search", type=str, help="CLI: search query")
    parser.add_argument("--download", type=str, help="CLI: manga ID to download")
    parser.add_argument(
        "--format", choices=["epub", "cbz", "pdf", "images"],
        default=None, help="Output format"
    )
    parser.add_argument("--chapters", type=str, help="Chapter range e.g. 1-50")
    parser.add_argument("--volumes", type=str, help="Volume range e.g. 1-10")
    parser.add_argument("--language", type=str, default="en", help="Language code")
    parser.add_argument("--output", type=str, help="Output directory")
    parser.add_argument(
        "--reading-direction", choices=["rtl", "ltr", "vertical"],
        default=None, help="Reading direction"
    )
    parser.add_argument("--headless-api", action="store_true", help="Start REST API only")
    parser.add_argument("--config", type=str, help="Config file path")

    args = parser.parse_args()

    config = Config(args.config)
    if args.output:
        config.set("output_dir", args.output)
    if args.format:
        config.set("default_format", args.format)
    if args.language:
        config.set("language", args.language)
    if args.reading_direction:
        config.set("reading_direction", args.reading_direction)

    logger = Logger(config)
    logger.info(f"{APP_NAME} v{VERSION} starting in {args.mode} mode")

    aggregator = Aggregator(config, logger)
    queue_manager = QueueManager(config, logger)
    download_engine = DownloadEngine(config, logger, aggregator)

    app_context = {
        "config": config,
        "logger": logger,
        "aggregator": aggregator,
        "queue_manager": queue_manager,
        "download_engine": download_engine,
        "version": VERSION,
        "app_name": APP_NAME,
    }

    if args.mode == "cli":
        run_cli(args, app_context)
    elif args.mode == "gui":
        run_gui(app_context)
    elif args.mode == "tui":
        run_tui(app_context)
    elif args.mode == "web":
        run_web(args, app_context)
    elif args.mode == "headless":
        run_web(args, app_context, headless=True)


def run_cli(args, ctx):
    aggregator = ctx["aggregator"]
    download_engine = ctx["download_engine"]
    logger = ctx["logger"]

    if args.search:
        logger.info(f"Searching: {args.search}")
        results = aggregator.search(args.search, language=args.language)
        if not results:
            print("No results found.")
            return
        for i, r in enumerate(results):
            sources = ", ".join(r.get("sources", []))
            print(f"  [{i+1}] {r['title']} ({sources}) - {r.get('chapter_count', '?')} chapters")
        return

    if args.download:
        chapter_range = parse_range(args.chapters) if args.chapters else None
        volume_range = parse_range(args.volumes) if args.volumes else None

        download_engine.download(
            manga_id=args.download,
            chapter_range=chapter_range,
            volume_range=volume_range,
            output_format=args.format or ctx["config"].get("default_format", "cbz"),
        )
        return

    print("Use --search or --download. See --help for options.")


def run_gui(ctx):
    from gui.GUI import MangadeckGUI
    app = MangadeckGUI(ctx)
    app.run()


def run_tui(ctx):
    from tui.TUI import MangadeckTUI
    app = MangadeckTUI(ctx)
    app.run()


def run_web(args, ctx, headless=False):
    from web.server import create_app
    app = create_app(ctx)
    print(f"\n  {APP_NAME} Dashboard: http://{args.host}:{args.port}\n")
    if headless:
        print("  Running in headless API mode")
    app.run(host=args.host, port=args.port, debug=False, threaded=True)


def parse_range(range_str):
    """Parse '1-50' or '1,3,5,7-10' into list of numbers."""
    if not range_str:
        return None
    result = []
    parts = range_str.split(",")
    for part in parts:
        part = part.strip()
        if "-" in part:
            try:
                start, end = part.split("-", 1)
                start = float(start)
                end = float(end)
                current = start
                while current <= end:
                    result.append(current)
                    if current == int(current):
                        current = int(current) + 1
                    else:
                        current = round(current + 1, 1)
            except ValueError:
                continue
        else:
            try:
                result.append(float(part))
            except ValueError:
                continue
    return sorted(set(result))


if __name__ == "__main__":
    main()