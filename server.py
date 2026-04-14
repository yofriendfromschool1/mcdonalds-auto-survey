"""
McDonald's Auto Survey — Flask Web Server
Serves the web frontend and provides API endpoints for running surveys.
"""

import os
import sys
import json
import uuid
import threading
from datetime import datetime

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from auto_survey import (
    run_with_receipt_code,
    run_with_store_info,
    set_status_callback,
    RESULTS_PATH,
)

app = Flask(__name__, static_folder="static", template_folder="static")
CORS(app)

# ---------------------------------------------------------------------------
# In-memory job tracking
# ---------------------------------------------------------------------------
jobs = {}
jobs_lock = threading.Lock()


def create_job():
    job_id = str(uuid.uuid4())[:8]
    with jobs_lock:
        jobs[job_id] = {
            "id": job_id,
            "status": "pending",
            "progress": 0,
            "message": "Queued...",
            "validation_code": None,
            "error": None,
            "created_at": datetime.now().isoformat(),
            "updates": [],
        }
    return job_id


def update_job(job_id, data):
    with jobs_lock:
        if job_id in jobs:
            job = jobs[job_id]
            if data.get("message"):
                job["message"] = data["message"]
            if data.get("progress") is not None:
                job["progress"] = data["progress"]
            if data.get("code"):
                job["validation_code"] = data["code"]
                job["status"] = "completed"
            if data.get("error"):
                job["error"] = data["error"]
                job["status"] = "failed"
            job["updates"].append({
                "message": data.get("message", ""),
                "progress": data.get("progress", 0),
                "timestamp": data.get("timestamp", datetime.now().isoformat()),
            })


# ---------------------------------------------------------------------------
# Survey runner thread
# ---------------------------------------------------------------------------
def run_survey_thread(job_id, mode, params):
    """Run a survey in a background thread."""
    def status_cb(data):
        update_job(job_id, data)

    set_status_callback(status_cb)

    with jobs_lock:
        jobs[job_id]["status"] = "running"

    try:
        if mode == "receipt_code":
            result = run_with_receipt_code(params["code"], headless=True)
        elif mode == "store_info":
            result = run_with_store_info(
                params["store_number"],
                params.get("ks_number", "01"),
                headless=True,
            )
        else:
            result = {"success": False, "error": f"Unknown mode: {mode}"}

        with jobs_lock:
            if result.get("success"):
                jobs[job_id]["validation_code"] = result["validation_code"]
                jobs[job_id]["status"] = "completed"
                jobs[job_id]["message"] = f"Done! Code: {result['validation_code']}"
                jobs[job_id]["progress"] = 100
            else:
                jobs[job_id]["error"] = result.get("error", "Unknown error")
                jobs[job_id]["status"] = "failed"
                jobs[job_id]["message"] = f"Failed: {result.get('error', 'Unknown')}"

    except Exception as e:
        with jobs_lock:
            jobs[job_id]["error"] = str(e)
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["message"] = f"Error: {str(e)}"

    finally:
        set_status_callback(None)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/survey", methods=["POST"])
def start_survey():
    """Start a new survey job."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body provided"}), 400

    mode = data.get("mode", "receipt_code")

    if mode == "receipt_code":
        code = data.get("code", "").strip()
        if not code:
            return jsonify({"error": "No receipt code provided"}), 400
        params = {"code": code}
    elif mode == "store_info":
        store = data.get("store_number", "").strip()
        if not store:
            return jsonify({"error": "No store number provided"}), 400
        params = {
            "store_number": store,
            "ks_number": data.get("ks_number", "01"),
        }
    else:
        return jsonify({"error": f"Unknown mode: {mode}"}), 400

    job_id = create_job()

    thread = threading.Thread(target=run_survey_thread, args=(job_id, mode, params), daemon=True)
    thread.start()

    return jsonify({"job_id": job_id, "status": "started"})


@app.route("/api/status/<job_id>")
def get_status(job_id):
    """Get the status of a survey job."""
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/api/history")
def get_history():
    """Get past survey results."""
    if os.path.exists(RESULTS_PATH):
        try:
            with open(RESULTS_PATH, "r") as f:
                results = json.load(f)
            return jsonify(results)
        except Exception:
            return jsonify([])
    return jsonify([])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n🍔 McDVOICE Auto Survey Web UI")
    print(f"   Open http://localhost:{port} in your browser\n")
    app.run(host="0.0.0.0", port=port, debug=True)
