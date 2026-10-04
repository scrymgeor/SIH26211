# DPOP prototype: Decentralized Proof-of-Procurement
SIH 2026 · PS26211 · Team The W.A.L.L.

React frontend + FastAPI backend simulating the full DPOP pipeline:
smart card + thumb → signed scale payload → vision assay → 3-of-3 consensus → escrow payout → hash-chained ledger.

## Run it (two terminals)

**1. Backend**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --port 8000 --reload
```

**2. Frontend**
```bash
npm install
npm run dev        # http://localhost:5173  (proxies /api to :8000)
```

## What's real vs simulated
- **Real:** ECDSA P-256 device signatures, 3-of-3 consensus rules, MSP escrow formula, hash-chained ledger with tamper detection, fail-secure halts.
- **Simulated:** ESP32 / HX711 / NFC hardware (UI controls), Match-on-Card (a boolean), Hyperledger / Polygon / IPFS (in-memory chain, CID derived from the image hash).
- **Vision:** a colour heuristic stands in for YOLOv8 so the demo runs anywhere. To use real YOLOv8:
  ```bash
  pip install ultralytics
  export DPOP_YOLO_WEIGHTS=path/to/your_grain_model.pt   # fine-tuned on grain / foreign-matter images
  ```
  Detections then come from YOLO; the crop classifier stays heuristic until you train crop classes.

MSP rates in `backend/main.py` are demo values; update them to the notified rates.

## Demo flow (about 2 minutes)
1. **Intake terminal:** defaults, then *Tap card & weigh*. Payout is released.
2. **Threat lab:** identity hijack, weight tampering, stones in the sack. Each is blocked by a different oracle.
3. **Audit dashboard:** click *Tamper* on a block and ledger integrity turns red.
