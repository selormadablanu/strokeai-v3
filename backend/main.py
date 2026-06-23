"""
StrokeAI Backend - runs on port 9000
Serves the frontend HTML AND the prediction API from one server.
Open browser at: http://localhost:9000
"""

import os, io, base64, logging, asyncio
from contextlib import asynccontextmanager
from typing import List
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from PIL import Image
from dotenv import load_dotenv

from model_utils import load_model, batch_predict, aggregate
from xai_utils import make_heatmap

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

INTERP    = None
ALLOWED   = {"image/jpeg","image/png","image/webp","image/bmp"}
MAX_FILES = 10
MAX_BYTES = 15 * 1024 * 1024

# Frontend is ../frontend/index.html relative to this file
FRONTEND = Path(__file__).parent.parent / "frontend" / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global INTERP
    model_path = os.getenv("MODEL_PATH", "xception_stroke_model.tflite")
    INTERP = load_model(model_path)
    logger.info("Ready. Frontend: " + str(FRONTEND))
    yield


app = FastAPI(lifespan=lifespan)

# Allow everything - no CORS issues
app.add_middleware(CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"],
    allow_headers=["*"], allow_credentials=True)


@app.get("/")
async def root():
    """Serve the frontend HTML page"""
    if not FRONTEND.exists():
        return HTMLResponse(f"""
        <html><body style="background:#111;color:#fff;font-family:sans-serif;padding:40px">
        <h2>⚠️ Cannot find frontend/index.html</h2>
        <p>Expected at: {FRONTEND}</p>
        <p>Make sure the folder structure is:</p>
        <pre>strokeai-v4/
  backend/   (this server)
  frontend/
    index.html</pre>
        </body></html>""", status_code=500)
    html = FRONTEND.read_text(encoding="utf-8")
    return HTMLResponse(content=html)


@app.get("/health")
async def health():
    return {
        "status":       "ok",
        "model_loaded": INTERP is not None,
        "demo_mode":    INTERP is None,
        "port":         9000,
        "version":      "4.0.0"
    }


@app.post("/predict")
async def predict_endpoint(files: List[UploadFile] = File(...)):
    if not files:            raise HTTPException(400, "No files.")
    if len(files)>MAX_FILES: raise HTTPException(400, f"Max {MAX_FILES}.")

    payloads = []
    for f in files:
        if f.content_type not in ALLOWED:
            raise HTTPException(400, f"Bad type: {f.content_type}")
        data = await f.read()
        if not data:           raise HTTPException(400, f"Empty: {f.filename}")
        if len(data)>MAX_BYTES: raise HTTPException(413, f"Too large: {f.filename}")
        try: Image.open(io.BytesIO(data)).verify()
        except: raise HTTPException(400, f"Invalid image: {f.filename}")
        payloads.append((f.filename or f"scan_{len(payloads)+1}", data))

    names, images = zip(*payloads)

    try:
        results = await asyncio.to_thread(batch_predict, INTERP, list(images))
    except Exception as e:
        raise HTTPException(500, f"Inference error: {e}")

    # XAI heatmaps for stroke cases
    async def xai(label, img):
        if label != "Stroke": return None
        return await asyncio.to_thread(make_heatmap, INTERP, img)

    heatmaps = await asyncio.gather(*[xai(l, img) for (l,_), img in zip(results, images)])

    individual = [
        {"filename": names[i], "prediction": l, "confidence": round(c,6), "heatmap": heatmaps[i]}
        for i,(l,c) in enumerate(results)
    ]

    final_label, final_conf = aggregate(results)

    # Explanation
    explanation = await asyncio.to_thread(
        get_explanation, final_label, final_conf, len(images), images[0])

    return JSONResponse({
        "prediction":         final_label,
        "confidence":         final_conf,
        "individual_results": individual,
        "explanation":        explanation,
        "xai_images":         [h for h in heatmaps if h],
    })


def get_explanation(label, conf, n, img_bytes):
    key = os.getenv("ANTHROPIC_API_KEY","")
    if not key or key == "your-key-here":
        return fallback(label, conf, n)
    try:
        import anthropic
        b64 = base64.standard_b64encode(img_bytes).decode()
        c   = anthropic.Anthropic(api_key=key)
        m   = c.messages.create(model="claude-opus-4-5", max_tokens=350,
            messages=[{"role":"user","content":[
                {"type":"image","source":{"type":"base64","media_type":"image/jpeg","data":b64}},
                {"type":"text","text":
                    f"AI brain scan result: {label} ({conf:.1%}, {n} scans). "
                    "Give: 1) Simple explanation 2) Clinical interpretation "
                    "3) Next steps 4) Disclaimer. Be concise."}]}])
        return m.content[0].text
    except Exception as e:
        logger.warning(f"Claude: {e}")
        return fallback(label, conf, n)


def fallback(label, conf, n):
    p = f"{conf:.1%}"
    if label == "Stroke":
        return (
            f"Stroke indicators detected in {n} scan(s) with {p} confidence.\n\n"
            "Clinical Interpretation: XAI heatmap highlights regions of concern — "
            "potentially hypodense tissue or asymmetry consistent with ischemic injury.\n\n"
            "Next Steps: Seek immediate emergency neurological evaluation.\n\n"
            "⚕️ Disclaimer: Research tool only. Not a medical diagnosis."
        )
    return (
        f"No stroke indicators in {n} scan(s) ({p} confidence).\n\n"
        "Clinical Interpretation: Scans appear within normal limits.\n\n"
        "Next Steps: If symptoms persist, consult a neurologist.\n\n"
        "⚕️ Disclaimer: Research tool only. Not a medical diagnosis."
    )
