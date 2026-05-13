"""
Flask server providing the web dashboard and REST API endpoints.
"""

import os
import json
import time
import math
import threading
from typing import Dict, Any

from flask import (
    Flask, render_template, request, jsonify,
    send_from_directory, Response, stream_with_context,
)

from core.notifier import Notifier


# ── JSON safety ────────────────────────────────────────────────────────────

def _sanitize(obj: Any, _seen=None) -> Any:
    """
    Recursively make an object JSON-safe.
    - Removes circular references
    - Converts non-serialisable types to strings
    - Replaces NaN/Inf floats with None
    """
    if _seen is None:
        _seen = set()

    obj_id = id(obj)

    if isinstance(obj, dict):
        if obj_id in _seen:
            return {}
        _seen.add(obj_id)
        result = {str(k): _sanitize(v, _seen) for k, v in obj.items()}
        _seen.discard(obj_id)
        return result

    if isinstance(obj, (list, tuple)):
        if obj_id in _seen:
            return []
        _seen.add(obj_id)
        result = [_sanitize(v, _seen) for v in obj]
        _seen.discard(obj_id)
        return result if isinstance(obj, list) else result

    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj

    if isinstance(obj, (str, int, bool)) or obj is None:
        return obj

    # Fallback for unknown types
    try:
        return str(obj)
    except Exception:
        return None


def safe_json(data: Any, status: int = 200) -> Response:
    """Return a Flask JSON response guaranteed to not raise TypeError."""
    try:
        clean = _sanitize(data)
        return Response(
            json.dumps(clean, ensure_ascii=False),
            status=status,
            mimetype="application/json",
        )
    except Exception as e:
        return Response(
            json.dumps({"error": f"Serialisation error: {e}"}),
            status=500,
            mimetype="application/json",
        )


# ── App factory ────────────────────────────────────────────────────────────

def create_app(ctx: Dict) -> Flask:

    config       = ctx["config"]
    logger       = ctx["logger"]
    aggregator   = ctx["aggregator"]
    queue_manager   = ctx["queue_manager"]
    download_engine = ctx["download_engine"]
    notifier     = Notifier(config, logger)

    queue_manager.set_download_engine(download_engine)
    queue_manager.set_on_complete(
        lambda: notifier.notify(
            "Queue Complete",
            "All queued downloads have finished.",
            "queue_complete",
        )
    )

    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    static_dir   = os.path.join(os.path.dirname(__file__), "static")

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    app.config["JSON_SORT_KEYS"] = False

    # ── favicon (suppress 404 noise) ────────────────────────────────────────
    @app.route("/favicon.ico")
    def favicon():
        return "", 204

    # ── Pages ────────────────────────────────────────────────────────────────
    @app.route("/")
    def index():
        return render_template("dash.html")

    # ── Search ───────────────────────────────────────────────────────────────
    @app.route("/api/search")
    def api_search():
        query    = request.args.get("q", "").strip()
        language = request.args.get("lang", config.get("language", "en"))
        page     = request.args.get("page", 1, type=int)
        sources  = request.args.get("sources", "")
        source_list = [s.strip() for s in sources.split(",") if s.strip()] or None

        if not query:
            return safe_json({"results": [], "query": ""})

        try:
            results = aggregator.search(query, language, page, source_list)
            return safe_json({
                "results": results,
                "query":   query,
                "page":    page,
                "language": language,
                "count":   len(results),
            })
        except Exception as e:
            logger.error(f"[API] Search error: {e}", category="api")
            return safe_json({"error": str(e), "results": []}, 500)

    @app.route("/api/trending")
    def api_trending():
        language = request.args.get("lang", config.get("language", "en"))
        page     = request.args.get("page", 1, type=int)
        try:
            results = aggregator.get_trending(language, page)
            return safe_json({"results": results, "count": len(results)})
        except Exception as e:
            logger.error(f"[API] Trending error: {e}", category="api")
            return safe_json({"error": str(e), "results": []}, 500)

    # ── Manga details ─────────────────────────────────────────────────────────
    @app.route("/api/manga/<manga_id>")
    def api_manga_details(manga_id):
        source = request.args.get("source") or None
        try:
            details = aggregator.get_manga_details(manga_id, source)
            if not details:
                return safe_json({"error": "Manga not found"}, 404)
            return safe_json(details)
        except Exception as e:
            logger.error(f"[API] Details error: {e}", category="api")
            return safe_json({"error": str(e)}, 500)

    @app.route("/api/manga/<manga_id>/chapters")
    def api_manga_chapters(manga_id):
        language  = request.args.get("lang", config.get("language", "en"))
        aggregate = request.args.get("aggregate", "true").lower() == "true"
        title     = request.args.get("title", "")
        try:
            source_ids = json.loads(request.args.get("source_ids", "{}"))
        except (json.JSONDecodeError, TypeError):
            source_ids = {}

        try:
            if aggregate and title:
                chapters, source_map = aggregator.get_complete_chapters(
                    manga_id, title=title, language=language, source_ids=source_ids,
                )
                return safe_json({
                    "chapters":   chapters,
                    "source_map": {k: len(v) for k, v in source_map.items()},
                    "total":      len(chapters),
                    "aggregated": True,
                })
            else:
                source = request.args.get("source") or None
                api    = aggregator.get_api(source) if source else aggregator._api_from_id(manga_id)
                chapters = api.get_chapters(manga_id, language) if api else []
                return safe_json({"chapters": chapters, "total": len(chapters), "aggregated": False})
        except Exception as e:
            logger.error(f"[API] Chapters error: {e}", category="api")
            return safe_json({"error": str(e), "chapters": []}, 500)

    @app.route("/api/manga/<manga_id>/volumes")
    def api_manga_volumes(manga_id):
        language = request.args.get("lang", config.get("language", "en"))
        title = request.args.get("title", "")
        try:
            source_ids = json.loads(request.args.get("source_ids", "{}"))
        except (json.JSONDecodeError, TypeError):
            source_ids = {}

        try:
            if title:
                volumes = aggregator.get_complete_volumes(
                    manga_id, title=title, language=language,
                    source_ids=source_ids,
                )
            else:
                source = request.args.get("source") or None
                api_obj = aggregator.get_api(source) if source else aggregator._api_from_id(manga_id)
                if api_obj:
                    volumes = api_obj.get_volumes(manga_id, language)
                else:
                    volumes = {}

            clean = {}
            for vol_key, chs in volumes.items():
                clean[str(vol_key)] = [
                    {
                        "id": c.get("id", ""),
                        "source_id": c.get("source_id", ""),
                        "chapter_number": c.get("chapter_number", 0),
                        "volume_number": c.get("volume_number"),
                        "title": c.get("title", ""),
                        "source": c.get("source", ""),
                    }
                    for c in chs
                ]
            return safe_json({"volumes": clean, "total": len(clean)})
        except Exception as e:
            logger.error(f"[API] Volumes error: {e}", category="api")
            return safe_json({"error": str(e)}, 500)


    # ── Download ──────────────────────────────────────────────────────────────
    @app.route("/api/download", methods=["POST"])
    def api_download():
        data = request.get_json() or {}
        manga_id  = data.get("manga_id", "")
        title     = data.get("title", "")
        source    = data.get("source", "")
        source_ids = data.get("source_ids", {})
        fmt       = data.get("format", config.get("default_format", "cbz"))
        ch_range  = data.get("chapter_range")
        vol_range = data.get("volume_range")
        language  = data.get("language", config.get("language", "en"))
        reading_direction = data.get("reading_direction")

        if not manga_id:
            return safe_json({"error": "manga_id required"}, 400)

        try:
            task_id = download_engine.download(
                manga_id=manga_id,
                chapter_range=ch_range,
                volume_range=vol_range,
                output_format=fmt,
                language=language,
                title=title,
                source=source,
                source_ids=source_ids,
                reading_direction=reading_direction,
                on_complete=lambda tid, info: notifier.notify(
                    "Download Complete",
                    f"{info.get('title', '')} finished.",
                    "complete",
                ),
            )
            return safe_json({"task_id": task_id, "status": "started"})
        except Exception as e:
            logger.error(f"[API] Download error: {e}", category="api")
            return safe_json({"error": str(e)}, 500)

    @app.route("/api/download/<task_id>")
    def api_download_status(task_id):
        status = download_engine.get_task(task_id)
        if status:
            return safe_json(status)
        return safe_json({"error": "Task not found"}, 404)

    @app.route("/api/downloads")
    def api_all_downloads():
        tasks = download_engine.get_all_tasks()
        stats = download_engine.get_stats()
        return safe_json({"tasks": tasks, "stats": stats})

    @app.route("/api/download/<task_id>/cancel", methods=["POST"])
    def api_cancel_download(task_id):
        ok = download_engine.cancel_task(task_id)
        return safe_json({"cancelled": ok})

    @app.route("/api/downloads/clear", methods=["POST"])
    def api_clear_downloads():
        download_engine.clear_completed()
        return safe_json({"cleared": True})

    # ── Cart ──────────────────────────────────────────────────────────────────
    @app.route("/api/cart")
    def api_get_cart():
        return safe_json({
            "items": queue_manager.get_cart(),
            "count": queue_manager.get_cart_count(),
        })

    @app.route("/api/cart/add", methods=["POST"])
    def api_add_to_cart():
        data = request.get_json() or {}
        try:
            item_id = queue_manager.add_to_cart(
                manga_id=data.get("manga_id", ""),
                title=data.get("title", ""),
                source=data.get("source", ""),
                source_ids=data.get("source_ids", {}),
                cover_url=data.get("cover_url", ""),
                output_format=data.get("format"),
                chapter_range=data.get("chapter_range"),
                volume_range=data.get("volume_range"),
                language=data.get("language"),
                reading_direction=data.get("reading_direction"),
            )
            return safe_json({"id": item_id, "added": True})
        except Exception as e:
            return safe_json({"error": str(e)}, 500)

    @app.route("/api/cart/<item_id>", methods=["DELETE"])
    def api_remove_from_cart(item_id):
        ok = queue_manager.remove_from_cart(item_id)
        return safe_json({"removed": ok})

    @app.route("/api/cart/clear", methods=["POST"])
    def api_clear_cart():
        queue_manager.clear_cart()
        return safe_json({"cleared": True})

    # ── Queue ─────────────────────────────────────────────────────────────────
    @app.route("/api/queue")
    def api_get_queue():
        return safe_json({
            "items":      queue_manager.get_queue(),
            "count":      queue_manager.get_queue_count(),
            "processing": queue_manager.is_processing(),
            "stats":      queue_manager.get_stats(),
        })

    @app.route("/api/queue/start", methods=["POST"])
    def api_start_queue():
        data = request.get_json() or {}
        enqueue_cart = data.get("enqueue_cart", True)
        count = 0
        if enqueue_cart:
            count = queue_manager.enqueue_cart()
        queue_manager.start_processing()
        return safe_json({"started": True, "enqueued": count})

    @app.route("/api/queue/stop", methods=["POST"])
    def api_stop_queue():
        queue_manager.stop_processing()
        return safe_json({"stopped": True})

    @app.route("/api/queue/<item_id>", methods=["DELETE"])
    def api_remove_from_queue(item_id):
        ok = queue_manager.remove_from_queue(item_id)
        return safe_json({"removed": ok})

    @app.route("/api/queue/clear", methods=["POST"])
    def api_clear_queue():
        queue_manager.clear_queue()
        return safe_json({"cleared": True})

    @app.route("/api/queue/history")
    def api_queue_history():
        return safe_json({"history": queue_manager.get_history()})

    # ── Config ────────────────────────────────────────────────────────────────
    @app.route("/api/config")
    def api_get_config():
        return safe_json(config.get_all())

    @app.route("/api/config", methods=["POST"])
    def api_set_config():
        data = request.get_json() or {}
        config.set_many(data)
        return safe_json({"saved": True, "config": config.get_all()})

    @app.route("/api/config/reset", methods=["POST"])
    def api_reset_config():
        key = request.args.get("key") or None
        config.reset(key)
        return safe_json({"reset": True, "config": config.get_all()})

    @app.route("/api/config/export")
    def api_export_config():
        return Response(
            config.export_config(),
            mimetype="application/json",
            headers={"Content-Disposition": "attachment; filename=mangadeck_config.json"},
        )

    @app.route("/api/config/import", methods=["POST"])
    def api_import_config():
        data = request.get_data(as_text=True)
        ok = config.import_config(data)
        return safe_json({"imported": ok})

    # ── Sources ───────────────────────────────────────────────────────────────
    @app.route("/api/sources")
    def api_sources():
        return safe_json({
            "sources":   aggregator.get_api_info(),
            "enabled":   aggregator.get_enabled_apis(),
            "languages": aggregator.get_supported_languages(),
        })

    @app.route("/api/sources/check")
    def api_check_sources():
        avail = aggregator.check_availability()
        return safe_json({"availability": avail})

    @app.route("/api/sources/enable", methods=["POST"])
    def api_enable_sources():
        data = request.get_json() or {}
        aggregator.set_enabled_apis(data.get("apis", []))
        return safe_json({"enabled": aggregator.get_enabled_apis()})

    # ── Logs ──────────────────────────────────────────────────────────────────
    @app.route("/api/logs")
    def api_logs():
        level    = request.args.get("level") or None
        category = request.args.get("category") or None
        source   = request.args.get("source") or None
        limit    = request.args.get("limit", 100, type=int)
        offset   = request.args.get("offset", 0, type=int)
        search   = request.args.get("search") or None

        logs  = logger.get_logs(level, category, source, limit, offset, search)
        stats = logger.get_stats()
        return safe_json({"logs": logs, "stats": stats})

    @app.route("/api/logs/clear", methods=["POST"])
    def api_clear_logs():
        logger.clear()
        return safe_json({"cleared": True})

    # ── Notifications ─────────────────────────────────────────────────────────
    @app.route("/api/notifications/test", methods=["POST"])
    def api_test_notifications():
        data    = request.get_json() or {}
        channel = data.get("channel", "desktop")
        results = {}

        if channel in ("desktop", "all"):
            notifier._desktop_notify("Mangadeck Test", "Desktop notifications working.")
            results["desktop"] = True

        if channel in ("discord", "all"):
            url = data.get("webhook_url", config.get("discord_webhook_url", ""))
            results["discord"] = notifier.test_discord(url)

        if channel in ("telegram", "all"):
            token   = data.get("bot_token", config.get("telegram_bot_token", ""))
            chat_id = data.get("chat_id", config.get("telegram_chat_id", ""))
            results["telegram"] = notifier.test_telegram(token, chat_id)

        return safe_json(results)

    # ── SSE ───────────────────────────────────────────────────────────────────
    @app.route("/api/events")
    def api_events():
        def event_stream():
            last_data = None
            while True:
                try:
                    tasks      = download_engine.get_all_tasks()
                    queue_stats = queue_manager.get_stats()
                    payload    = _sanitize({
                        "tasks":     tasks,
                        "queue":     queue_stats,
                        "timestamp": time.time(),
                    })
                    data = json.dumps(payload, ensure_ascii=False)
                    if data != last_data:
                        yield f"data: {data}\n\n"
                        last_data = data
                except Exception:
                    pass
                time.sleep(1)

        return Response(
            stream_with_context(event_stream()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control":    "no-cache",
                "Connection":       "keep-alive",
                "X-Accel-Buffering":"no",
            },
        )

    # ── System ────────────────────────────────────────────────────────────────
    @app.route("/api/system")
    def api_system():
        return safe_json({
            "version":        ctx["version"],
            "app_name":       ctx["app_name"],
            "output_dir":     config.get_output_dir(),
            "config_path":    config.get_config_path(),
            "download_stats": download_engine.get_stats(),
            "queue_stats":    queue_manager.get_stats(),
            "log_stats":      logger.get_stats(),
        })

    # ── Cover proxy ───────────────────────────────────────────────────────────
    @app.route("/api/proxy/image")
    def api_proxy_image():
        url = request.args.get("url", "")
        if not url:
            return "", 404
        try:
            import requests as _req
            resp = _req.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0",
                "Referer":    "/".join(url.split("/")[:3]) + "/",
            })
            if resp.status_code == 200:
                ct = resp.headers.get("Content-Type", "image/jpeg")
                return Response(
                    resp.content, mimetype=ct,
                    headers={"Cache-Control": "public, max-age=86400"},
                )
        except Exception:
            pass
        return "", 404

    return app