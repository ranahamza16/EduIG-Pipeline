import asyncio
import csv
import os
import sqlite3
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

app = FastAPI(title="EduIG-Pipeline Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TARGETS_FILE = "config/targets.csv"
DB_PATH = "data/eduig.db"


# --- Pydantic Models ---
class Target(BaseModel):
    target: str
    consent: str = "false"


class ProfileResponse(BaseModel):
    profile_id: Optional[str]
    username: str
    full_name: Optional[str]
    is_verified: Optional[bool]
    bio: Optional[str]
    followers: Optional[int]
    following: Optional[int]
    posts_count: Optional[int]
    extracted_at: Optional[str]
    source: Optional[str]


class RunResponse(BaseModel):
    run_id: str
    started_at: str
    completed_at: Optional[str]
    targets_count: Optional[int]
    success_count: Optional[int]


class TargetListResponse(BaseModel):
    targets: List[Target]


# --- Helper Functions ---
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_all_targets() -> List[Dict[str, str]]:
    if not os.path.exists(TARGETS_FILE):
        return []
    targets = []
    with open(TARGETS_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # Handle the "# target" vs "target" header issue
        target_key = next((k for k in reader.fieldnames if "target" in k.lower()), "target")
        consent_key = next((k for k in reader.fieldnames if "consent" in k.lower()), "consent")
        for row in reader:
            if not row.get(target_key):
                continue
            t = row[target_key].strip()
            if not t:
                continue
            c = row.get(consent_key, "false").strip().lower()
            targets.append({"target": t, "consent": c})
    return targets


def write_targets(targets: List[Dict[str, str]]):
    with open(TARGETS_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["# target", "consent"])
        writer.writeheader()
        for t in targets:
            writer.writerow({"# target": t["target"], "consent": t["consent"]})


# --- API Endpoints ---
@app.get("/api/targets", response_model=TargetListResponse)
async def list_targets():
    return {"targets": get_all_targets()}


@app.post("/api/targets", response_model=TargetListResponse)
async def add_target(target_req: Target):
    target = target_req.target.strip()
    consent = target_req.consent.strip().lower()

    if not target:
        raise HTTPException(status_code=400, detail="Target is required")

    targets = get_all_targets()
    if any(t["target"] == target for t in targets):
        raise HTTPException(status_code=400, detail="Target already exists")

    targets.append({"target": target, "consent": consent})
    write_targets(targets)
    return {"targets": targets}


@app.delete("/api/targets/{target}", response_model=TargetListResponse)
async def delete_target(target: str):
    targets = get_all_targets()
    new_targets = [t for t in targets if t["target"] != target]
    if len(targets) == len(new_targets):
        raise HTTPException(status_code=404, detail="Target not found")

    write_targets(new_targets)
    return {"targets": new_targets}


@app.get("/api/data/profiles", response_model=List[ProfileResponse])
async def get_profiles(limit: int = 100, offset: int = 0):
    if not os.path.exists(DB_PATH):
        return []
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM profiles ORDER BY extracted_at DESC LIMIT ? OFFSET ?", (limit, offset)
    )
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


@app.get("/api/data/runs", response_model=List[RunResponse])
async def get_runs(limit: int = 100, offset: int = 0):
    if not os.path.exists(DB_PATH):
        return []
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM runs ORDER BY started_at DESC LIMIT ? OFFSET ?", (limit, offset))
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


@app.post("/api/run")
async def run_pipeline():
    async def log_generator():
        import sys

        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "run.py",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        yield "data: Pipeline started...\n\n"

        while True:
            line = await process.stdout.readline()
            if not line:
                break
            yield f"data: {line.decode('utf-8')}\n\n"

        await process.wait()
        yield f"data: Pipeline finished with exit code {process.returncode}\n\n"

    return StreamingResponse(log_generator(), media_type="text/event-stream")


# Mount React static files
frontend_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist"
)
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
else:

    @app.get("/")
    async def index_placeholder():
        return HTMLResponse("<h1>Frontend not built yet. Run Vite build.</h1>")


if __name__ == "__main__":
    import sys

    import uvicorn

    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    uvicorn.run(app, host="127.0.0.1", port=8000)
