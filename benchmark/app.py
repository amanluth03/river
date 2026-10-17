"""Local web app: one page to run the benchmark, review every value with its source, and export."""
import tempfile
import threading
import webbrowser
from datetime import date
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel

from . import config, export_excel, pipeline

STATIC = Path(__file__).parent / "static"
RUNS_DIR = config.RUNS_DIR

app = FastAPI(title="Apex Ridge peer benchmark")
# Only answer requests addressed to this machine. Blocks DNS-rebinding: a web page that points its own
# domain at 127.0.0.1 still sends its own Host header, which is refused here.
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class Runner:
    """Runs one pipeline at a time in a background thread and remembers its last message."""

    def __init__(self):
        self.thread: threading.Thread | None = None
        self.message = ""
        self.error = ""

    @property
    def running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def start(self, as_of: date):
        self.message, self.error = "Starting…", ""

        def work():
            try:
                pipeline.run(as_of=as_of, progress=self._progress, runs_dir=RUNS_DIR)
            except Exception as exc:  # shown to the analyst; the run log keeps the details
                self.error = f"Run failed: {exc}"

        self.thread = threading.Thread(target=work, daemon=True)
        self.thread.start()

    def _progress(self, message: str):
        self.message = message


RUNNER = Runner()


class RunRequest(BaseModel):
    as_of: date


@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC / "index.html").read_text()


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/api/bundle")
def bundle():
    latest = pipeline.latest_bundle(RUNS_DIR)
    if latest is None:
        return JSONResponse({}, status_code=404)
    return Response(latest.model_dump_json(), media_type="application/json")


@app.post("/api/run", status_code=202)
def run(req: RunRequest):
    if req.as_of not in config.window_quarters(req.as_of, count=1):
        raise HTTPException(400, "Choose a calendar quarter-end (Mar 31, Jun 30, Sep 30 or Dec 31).")
    if RUNNER.running:
        raise HTTPException(409, "A run is already in progress.")
    RUNNER.start(req.as_of)
    return {"started": True}


@app.get("/api/status")
def status():
    return {"running": RUNNER.running, "message": RUNNER.message, "error": RUNNER.error}


@app.get("/api/export.xlsx")
def export():
    latest = pipeline.latest_bundle(RUNS_DIR)
    if latest is None:
        raise HTTPException(404, "Run the benchmark first.")
    out = Path(tempfile.mkdtemp()) / f"peer_benchmark_{latest.as_of}.xlsx"
    export_excel.write(latest, out)
    return FileResponse(out, filename=out.name,
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def main():
    url = "http://127.0.0.1:8000"
    print(f"Peer benchmark running at {url}  (Ctrl+C to stop)")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
