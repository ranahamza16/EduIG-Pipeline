import csv
import io
import json

from flask import Flask, Response, jsonify, render_template, request

from src.dashboard.queries import get_compliance_logs, get_profile_detail, get_profiles, get_stats

app = Flask(__name__)

# --- HTML Routes ---


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/offline.html")
def offline_page() -> str:
    return render_template("offline.html")


@app.route("/profiles")
def profiles_page() -> str:
    return render_template("profiles.html")


@app.route("/profile/<profile_id>")
def profile_detail_page(profile_id: str) -> str:
    return render_template("profile_detail.html", profile_id=profile_id)


@app.route("/compliance")
def compliance_page() -> str:
    return render_template("compliance.html")


@app.route("/settings")
def settings_page() -> str:
    return render_template("settings.html")


# --- API Routes ---


@app.route("/api/stats")
def api_stats() -> Response | tuple[Response, int]:
    try:
        stats = get_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/profiles")
def api_profiles() -> Response | tuple[Response, int]:
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 25, type=int)
        search = request.args.get("search", "")
        sort_by = request.args.get("sort_by", "extracted_at")
        order = request.args.get("order", "desc")

        result = get_profiles(
            page=page, per_page=per_page, search=search, sort_by=sort_by, order=order
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/profile/<profile_id>")
def api_profile_detail(profile_id: str) -> Response | tuple[Response, int]:
    try:
        detail = get_profile_detail(profile_id)
        if not detail:
            return jsonify({"error": "Profile not found"}), 404
        return jsonify(detail)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/compliance")
def api_compliance() -> Response | tuple[Response, int]:
    try:
        logs = get_compliance_logs()
        return jsonify(logs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/export/<format_type>")
def api_export(format_type: str) -> Response | tuple[Response, int]:
    try:
        # Get all profiles without pagination for export
        profiles_data = get_profiles(per_page=1000000)
        profiles = profiles_data["data"]

        if format_type == "json":
            return Response(
                json.dumps(profiles, indent=2),
                mimetype="application/json",
                headers={"Content-Disposition": "attachment;filename=profiles_export.json"},
            )
        elif format_type == "csv":
            if not profiles:
                return Response("No data", status=404)

            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=profiles[0].keys())
            writer.writeheader()
            writer.writerows(profiles)

            return Response(
                output.getvalue(),
                mimetype="text/csv",
                headers={"Content-Disposition": "attachment;filename=profiles_export.csv"},
            )
        else:
            return jsonify({"error": "Unsupported format"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
