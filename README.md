# 🏗️ Autonomous Structural Intelligence System

> A production-grade, 7-stage AI pipeline that parses 2D floor plan images, reconstructs 3D structural models, optimizes construction materials using Weighted Properties Method (WPM) with hard engineering constraints, generates evidence-based explanations via Gemini AI, and logs immutable audit trails on the Stellar blockchain.

---

## 🎯 Pipeline Stages

| Stage | Module | Technology | Purpose |
|-------|--------|------------|---------|
| 1 | `semantic_extractor.py` | Gemini 2.5 Flash VLM | Extract room topology, spans, and scale from floor plan images |
| 2 | `wall_extractor.py` | OpenCV + U-Net (ResNet34) | Isolate structural walls via morphological filtering + deep learning |
| 3 | `geometry_optimizer.py` | PuLP MIP Solver + NetworkX | Force noisy CV output into orthogonal, gap-free planar graphs |
| 4 | `model_generator.py` | Custom Python → Three.js | Convert 2D walls to 3D box meshes (no browser-side CSG) |
| 5 | `material_optimizer.py` | WPM Math Engine | Score materials with hard constraint: span > 5m → disqualify < 30 MPa |
| 6 | `explainer.py` | Gemini 2.5 Flash + MD5 Cache | Generate number-cited structural justifications |
| 7 | `contracts/structural_audit` | Stellar Soroban (Rust) | Immutable on-chain audit trail for every analysis |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- A [Gemini API Key](https://aistudio.google.com/apikey) (free tier)

### 1. Clone & Install

```bash
git clone <repo-url> && cd iiitNR

# Backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Frontend
cd frontend && npm install && cd ..
```

### 2. Run

```bash
# Terminal 1: Backend (from /backend directory)
cd backend && python -m uvicorn main:app --reload

# Terminal 2: Frontend
cd frontend && npm run dev
```

Open **http://localhost:5173** → Upload a floor plan → Click **Run Pipeline**.

---

## 📂 Project Structure

```
iiitNR/
├── backend/
│   ├── main.py                 # FastAPI orchestrator (7-stage pipeline)
│   ├── semantic_extractor.py   # Stage 1: Gemini VLM extraction
│   ├── wall_extractor.py       # Stage 2: CV wall segmentation
│   ├── geometry_optimizer.py   # Stage 3: MIP topological optimization
│   ├── model_generator.py      # Stage 4: 3D mesh generation (no-CSG)
│   ├── material_optimizer.py   # Stage 5: WPM material scoring
│   ├── explainer.py            # Stage 6: AI justification engine
│   ├── geometry.py             # Wall classification & span detection
│   ├── parser.py               # DL parsing (MitUNet + KeypointCNN)
│   └── models.py               # PyTorch model architectures
├── contracts/
│   └── structural_audit/       # Soroban smart contract (Rust)
│       └── src/lib.rs
├── frontend/
│   └── src/
│       ├── App.jsx             # 3-panel glassmorphic dashboard
│       └── components/
│           └── ModelViewer.jsx  # Three.js WebGL renderer
├── sample_inputs/              # Test floor plans (A, B, C)
├── tests/                      # Unit tests
├── requirements.txt
└── .env.example
```

---

## 🧪 Key Engineering Decisions

- **No-CSG Frontend**: All boolean geometry operations (splitting walls at openings) are performed in Python. The frontend only renders pre-computed `BoxGeometry` meshes.
- **Hard Span Constraint**: If any room span exceeds 5.0m, materials with compressive strength < 30 MPa are automatically disqualified (score = 0).
- **Cache Invalidation**: Explanation cache keys are MD5 hashes of `(element_id, material_id, span_m)`, ensuring re-generation when structural dimensions change.

---

## 📜 License

MIT
