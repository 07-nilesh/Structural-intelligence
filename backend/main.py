"""
main.py — FastAPI backend + full pipeline orchestration

Endpoints:
  POST /analyze       — Upload floor plan → run full 5-stage pipeline
  GET  /api/model/{id} — Get 3D model JSON
  GET  /api/results/{id} — Get analysis results
  GET  /health        — Health check
"""

import os
import uuid
import json
import shutil
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from parser import parse_floor_plan
from geometry import reconstruct_geometry
from model_generator import generate_3d_model
from material_optimizer import recommend_all_materials
from explainer import generate_all_explanations

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Autonomous Structural Intelligence System",
    description="5-stage pipeline: Floor Plan → Parsing → Geometry → 3D Model → Materials → Explanations",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for analysis results
ANALYSES: dict = {}

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

SAMPLE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sample_inputs")
if os.path.exists(SAMPLE_DIR):
    app.mount("/sample_inputs", StaticFiles(directory=SAMPLE_DIR), name="sample_inputs")


# ---------------------------------------------------------------------------
# Stellar SDK integration (Web3 audit trail)
# ---------------------------------------------------------------------------
def log_to_stellar(lb_count: int, max_span: float) -> str:
    """
    Log analysis results to Stellar Soroban for immutable audit trail.
    Returns transaction hash or error message.
    """
    try:
        from stellar_sdk import (
            Server, Keypair, TransactionBuilder, Network
        )
        # NOTE: For production, use STELLAR_SECRET_KEY env var
        secret = os.environ.get("STELLAR_SECRET_KEY", "")
        if not secret:
            return "stellar_not_configured"

        keypair = Keypair.from_secret(secret)
        server = Server("https://horizon-testnet.stellar.org")
        account = server.load_account(keypair.public_key)

        tx = (
            TransactionBuilder(
                source_account=account,
                network_passphrase=Network.TESTNET_NETWORK_PASSPHRASE,
                base_fee=100,
            )
            .append_manage_data_op(
                data_name="structural_audit",
                data_value=json.dumps({
                    "lb_count": lb_count,
                    "max_span_m": round(max_span, 2),
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": "VERIFIED",
                }).encode(),
            )
            .set_timeout(30)
            .build()
        )
        tx.sign(keypair)
        response = server.submit_transaction(tx)
        return response.get("hash", "unknown")

    except ImportError:
        return "stellar_sdk_not_installed"
    except Exception as e:
        return f"stellar_error:{str(e)[:100]}"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


@app.post("/analyze")
async def analyze_floor_plan(
    file: UploadFile = File(...),
    plan_id: str = Form(default=None),
):
    """Full pipeline: upload image → parse → geometry → 3D → materials → explanations."""
    analysis_id = str(uuid.uuid4())[:8]

    # Save uploaded file
    ext = os.path.splitext(file.filename)[1] or ".png"
    image_path = os.path.join(UPLOAD_DIR, f"{analysis_id}{ext}")
    with open(image_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Infer plan_id from filename if not provided
    if not plan_id:
        basename = os.path.splitext(file.filename)[0].lower()
        for pid in ["plan_a", "plan_b", "plan_c"]:
            if pid in basename:
                plan_id = pid
                break

    # ── Stage 1: Parse ──
    parsed = parse_floor_plan(image_path, plan_id)
    fallback_used = parsed.get("fallback_used", False)

    # ── Stage 2: Geometry ──
    geometry = reconstruct_geometry(parsed)

    # ── Stage 3: 3D Model ──
    model = generate_3d_model(geometry)

    # ── Stage 4: Materials ──
    material_results = recommend_all_materials(geometry)

    # ── Stage 5: Explanations ──
    explanations = generate_all_explanations(geometry, material_results)

    # ── Web3: Stellar Audit ──
    lb_count = sum(
        1 for w in geometry["classified_walls"]
        if w["type"] == "load-bearing"
    )
    max_span = max(
        [c["span_m"] for c in geometry.get("structural_concerns", [])],
        default=0,
    )
    stellar_tx_hash = log_to_stellar(lb_count, max_span)

    # Build result
    result = {
        "analysis_id": analysis_id,
        "status": "success",
        "timestamp": datetime.utcnow().isoformat(),
        "fallback_used": fallback_used,
        "fallback_reason": parsed.get("fallback_reason", None),
        "summary": {
            "rooms_detected": len(parsed["rooms"]),
            "walls_detected": len(parsed["walls"]),
            "openings_detected": len(parsed.get("openings", [])),
            "load_bearing_walls": lb_count,
            "partition_walls": len(geometry["classified_walls"]) - lb_count,
            "structural_warnings_count": len(
                geometry.get("structural_concerns", [])
            ),
            "columns_required": len(geometry.get("columns_required", [])),
        },
        "parsed_data": parsed,
        "geometry": {
            "classified_walls": geometry["classified_walls"],
            "structural_concerns": geometry.get("structural_concerns", []),
            "columns_required": geometry.get("columns_required", []),
            "wall_graph": geometry.get("wall_graph", {}),
        },
        "model_3d": model,
        "recommendations": material_results,
        "explanations": explanations,
        "stellar_tx_hash": stellar_tx_hash,
    }

    ANALYSES[analysis_id] = result
    return JSONResponse(result)


@app.get("/api/model/{analysis_id}")
async def get_model(analysis_id: str):
    """Get 3D model data for a specific analysis."""
    if analysis_id not in ANALYSES:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return JSONResponse(ANALYSES[analysis_id]["model_3d"])


@app.get("/api/results/{analysis_id}")
async def get_results(analysis_id: str):
    """Get full analysis results."""
    if analysis_id not in ANALYSES:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return JSONResponse(ANALYSES[analysis_id])


@app.get("/api/analyses")
async def list_analyses():
    """List all completed analyses."""
    return JSONResponse({
        aid: {
            "timestamp": a["timestamp"],
            "rooms": a["summary"]["rooms_detected"],
            "walls": a["summary"]["walls_detected"],
            "fallback": a["fallback_used"],
        }
        for aid, a in ANALYSES.items()
    })


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
