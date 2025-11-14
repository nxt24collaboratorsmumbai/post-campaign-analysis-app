# src/main.py

from typing import List, Optional

import json

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv

from src.pca_core import run_pca_pipeline

load_dotenv()

app = FastAPI(title="Agentic PCA Backend")

# Allow your frontend (index.html) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/run-pca")
async def api_run_pca(
    snapshots: Optional[List[UploadFile]] = File(None),
    dataFile: Optional[UploadFile] = File(None),
    objective: str = Form(""),
    channels: str = Form("[]"),
):
    """
    Endpoint called from the dark HTML UI.

    FormData expected (from JS):
      - snapshots: multiple image files (PNG/JPG)   -> name="snapshots"
      - dataFile: CSV/XLSX file                     -> name="dataFile"
      - objective: string                           -> name="objective"
      - channels: JSON list string                  -> name="channels"
    """
    # Parse channels JSON
    try:
        channel_list = json.loads(channels) if channels else []
        if not isinstance(channel_list, list):
            channel_list = []
    except Exception:
        channel_list = []

    # Take the first snapshot only for now
    image_bytes = None
    if snapshots and len(snapshots) > 0:
        first = snapshots[0]
        image_bytes = await first.read()

    data_bytes = None
    data_filename = None
    if dataFile is not None:
        data_bytes = await dataFile.read()
        data_filename = dataFile.filename

    try:
        ppt_buf = run_pca_pipeline(
            image_bytes=image_bytes,
            data_bytes=data_bytes,
            data_filename=data_filename,
            objective=objective,
            channels=channel_list,
        )
    except Exception as e:
        # If anything crashes, return JSON error (frontend can log this)
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )

    return StreamingResponse(
        ppt_buf,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "presentationml.presentation"
        ),
        headers={"Content-Disposition": 'attachment; filename="PCA_Report.pptx"'},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
