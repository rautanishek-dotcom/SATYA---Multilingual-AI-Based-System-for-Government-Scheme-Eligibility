"""
scraper_status.py
─────────────────
Flask Blueprint that exposes:
  GET  /api/scraper/status        → last N scrape run logs
  GET  /api/scraper/stats         → scheme collection summary
  POST /api/scraper/trigger       → manually trigger a scrape (admin only)
"""

import subprocess
import sys
import os
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from database import get_db

scraper_bp = Blueprint("scraper", __name__)


# ────────────────────────────────────────────
# GET /api/scraper/status
# Returns the last 10 scrape run logs
# ────────────────────────────────────────────
@scraper_bp.route("/status", methods=["GET"])
def scraper_status():
    db = get_db()
    limit = int(request.args.get("limit", 10))

    logs = list(
        db["scrape_logs"]
        .find({}, {"_id": 0})
        .sort("run_at", -1)
        .limit(limit)
    )

    # Convert datetimes to ISO strings for JSON
    for log in logs:
        if isinstance(log.get("run_at"), datetime):
            log["run_at"] = log["run_at"].isoformat()

    return jsonify({
        "scrape_logs": logs,
        "total_runs": db["scrape_logs"].count_documents({})
    }), 200


# ────────────────────────────────────────────
# GET /api/scraper/stats
# Returns a summary of the schemes collection
# ────────────────────────────────────────────
@scraper_bp.route("/stats", methods=["GET"])
def scraper_stats():
    db = get_db()
    schemes_col = db["schemes"]

    total = schemes_col.count_documents({})
    by_source = list(schemes_col.aggregate([
        {"$group": {"_id": "$source", "count": {"$sum": 1}}}
    ]))
    by_state = list(schemes_col.aggregate([
        {"$group": {"_id": "$state", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]))

    # Last scraped date from scrape_logs
    last_log = db["scrape_logs"].find_one({}, sort=[("run_at", -1)])
    last_run = None
    if last_log and isinstance(last_log.get("run_at"), datetime):
        last_run = last_log["run_at"].isoformat()

    return jsonify({
        "total_schemes"   : total,
        "by_source"       : [{"source": s["_id"], "count": s["count"]} for s in by_source],
        "top_10_states"   : [{"state": s["_id"], "count": s["count"]} for s in by_state],
        "last_scrape_run" : last_run,
        "generated_at"    : datetime.now(timezone.utc).isoformat(),
    }), 200


# ────────────────────────────────────────────
# POST /api/scraper/trigger
# Manually trigger a scrape (admin-only guard via secret key)
# ────────────────────────────────────────────
@scraper_bp.route("/trigger", methods=["POST"])
def trigger_scraper():
    # Simple admin secret guard (set SCRAPER_SECRET in your .env)
    secret = os.getenv("SCRAPER_SECRET", "satya_admin_2024")
    provided = request.headers.get("X-Scraper-Secret", "")

    if provided != secret:
        return jsonify({"error": "Unauthorized. Provide correct X-Scraper-Secret header."}), 403

    # Find the scraper script path relative to this file
    scraper_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "scheme_scraper.py"
    )

    if not os.path.exists(scraper_path):
        return jsonify({"error": "scheme_scraper.py not found."}), 500

    try:
        # Run scraper in background (non-blocking)
        subprocess.Popen(
            [sys.executable, scraper_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        return jsonify({
            "message"    : "✅ Scraper triggered successfully in background.",
            "triggered_at": datetime.now(timezone.utc).isoformat(),
        }), 202

    except Exception as exc:
        return jsonify({"error": f"Failed to start scraper: {str(exc)}"}), 500
