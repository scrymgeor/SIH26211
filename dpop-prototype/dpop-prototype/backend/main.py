"""DPOP prototype backend (FastAPI).

Simulates the edge-to-ledger pipeline from the SIH slides:
  smart card + thumb  ->  signed scale payload  ->  vision assay  ->  3-of-3 consensus
  ->  escrow payout  ->  hash-chained ledger entry (stand-in for Hyperledger/Polygon + IPFS).

Hardware pieces (ESP32, HX711, PN532, Pi 5) are simulated; the cryptography, the
consensus rules and the ledger are real code.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import time
import uuid
from typing import Optional

import numpy as np
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel

app = FastAPI(title="DPOP prototype", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --------------------------------------------------------------------------- config
# Demo rates in Rs per quintal. Real MSPs are notified by the Government each season.
MSP_PER_QUINTAL = {"wheat": 2425.0, "paddy": 2369.0}
WEIGHT_LIMITS_KG = (5.0, 120.0)  # plausible single-sack range at one weigh station
FOREIGN_MATTER_LIMIT = 0.04  # fraction of sack area; above this, intake halts

# --------------------------------------------------------------------------- device keys
# On the real hardware these live in eFuse / a secure element and never leave the chip.
def _new_key() -> ec.EllipticCurvePrivateKey:
    return ec.generate_private_key(ec.SECP256R1())


DEVICES = {
    "SCALE-ESP32-0001": _new_key(),
    "VISION-PI5-0001": _new_key(),
}


def _pub_hex(key: ec.EllipticCurvePrivateKey) -> str:
    return key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    ).hex()


DEVICE_PUBKEYS = {dev: _pub_hex(k) for dev, k in DEVICES.items()}


def canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def sign(device_id: str, payload: dict) -> str:
    return DEVICES[device_id].sign(canonical(payload), ec.ECDSA(hashes.SHA256())).hex()


def verify(device_id: str, payload: dict, signature_hex: str) -> bool:
    pub = ec.EllipticCurvePublicKey.from_encoded_point(
        ec.SECP256R1(), bytes.fromhex(DEVICE_PUBKEYS[device_id])
    )
    try:
        pub.verify(bytes.fromhex(signature_hex), canonical(payload), ec.ECDSA(hashes.SHA256()))
        return True
    except (InvalidSignature, ValueError):
        return False


# --------------------------------------------------------------------------- farmers
# Match-on-Card: the template and the match live "inside the card". The server only ever
# sees a boolean result plus the card's own signature, never biometric data.
FARMERS = {
    "CARD-7F3A-1001": {"name": "Ramesh Yadav", "village": "Karnal, Haryana", "wallet": "0xA11CE0001"},
    "CARD-7F3A-1002": {"name": "Gurpreet Singh", "village": "Ludhiana, Punjab", "wallet": "0xA11CE0002"},
    "CARD-7F3A-1003": {"name": "Sunita Devi", "village": "Hoshiarpur, Punjab", "wallet": "0xA11CE0003"},
}


def match_on_card(card_id: str, finger: str) -> dict:
    farmer = FARMERS.get(card_id)
    if not farmer:
        return {"card_found": False, "match": False, "reason": "Unknown card"}
    ok = finger == "enrolled"
    return {
        "card_found": True,
        "match": ok,
        "reason": "Fingerprint matched inside secure element" if ok else "Thumbprint does not match card template",
    }


# --------------------------------------------------------------------------- ledger
LEDGER: list[dict] = []


def _block_hash(block: dict) -> str:
    body = {k: v for k, v in block.items() if k != "hash"}
    return hashlib.sha256(canonical(body)).hexdigest()


def append_block(kind: str, data: dict) -> dict:
    prev = LEDGER[-1]["hash"] if LEDGER else "0" * 64
    block = {
        "height": len(LEDGER),
        "timestamp": time.time(),
        "kind": kind,
        "data": data,
        "prev_hash": prev,
    }
    block["hash"] = _block_hash(block)
    LEDGER.append(block)
    return block


def verify_chain() -> dict:
    for i, b in enumerate(LEDGER):
        if _block_hash(b) != b["hash"]:
            return {"valid": False, "broken_at": i, "reason": "Block contents do not match their hash"}
        expected_prev = LEDGER[i - 1]["hash"] if i else "0" * 64
        if b["prev_hash"] != expected_prev:
            return {"valid": False, "broken_at": i, "reason": "prev_hash link is broken"}
    return {"valid": True, "broken_at": None, "reason": "All blocks verified"}


append_block("genesis", {"note": "DPOP prototype chain started", "devices": DEVICE_PUBKEYS})

# --------------------------------------------------------------------------- vision
def decode_image(b64: str) -> Image.Image:
    if "," in b64:
        b64 = b64.split(",", 1)[1]
    return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")


def _try_yolo(img: Image.Image) -> Optional[dict]:
    """Real YOLOv8 inference when `ultralytics` and a weights file are available."""
    try:
        from ultralytics import YOLO  # type: ignore
        import os

        weights = os.environ.get("DPOP_YOLO_WEIGHTS", "yolov8n.pt")
        model = YOLO(weights)
        res = model.predict(img, verbose=False)[0]
        boxes = []
        for b in res.boxes:
            x1, y1, x2, y2 = [float(v) for v in b.xyxy[0]]
            boxes.append(
                {
                    "label": res.names[int(b.cls[0])],
                    "conf": round(float(b.conf[0]), 3),
                    "box": [x1 / img.width, y1 / img.height, (x2 - x1) / img.width, (y2 - y1) / img.height],
                }
            )
        return {"engine": f"YOLOv8 ({weights})", "detections": boxes}
    except Exception:
        return None


def _heuristic_assay(img: Image.Image) -> dict:
    """Colour-based stand-in for the fine-tuned YOLOv8 grain model.

    Classifies the sack contents as wheat (golden-tan) / paddy (straw-yellow, lighter) and flags
    grey/dark blobs as foreign matter (stones, dirt). A custom-trained YOLOv8 model replaces this.
    """
    small = img.resize((128, 128))
    a = np.asarray(small).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(axis=-1), a.min(axis=-1)
    sat = (mx - mn) / (mx + 1e-6)

    grain = (r > g * 0.98) & (g > b * 1.15) & (sat > 0.22) & (mx > 110)
    stone = (sat < 0.16) & (mx > 40) & (mx < 190)  # grey
    dirt = (mx < 85) & (sat < 0.45)  # dark clumps

    # Region of interest: the camera is framed on the sack mouth, so only the central disc counts.
    yy, xx = np.mgrid[0:128, 0:128]
    roi = ((xx - 64) ** 2 + (yy - 64) ** 2) < (128 * 0.44) ** 2
    grain &= roi
    foreign = (stone | dirt) & roi
    n = int(roi.sum())
    grain_frac = float(grain.sum() / n)
    foreign_frac = float(foreign.sum() / n)

    # crop type: paddy husk is paler/yellower, wheat is deeper amber-brown
    if grain.sum() > 50:
        gr, gg, gb = r[grain].mean(), g[grain].mean(), b[grain].mean()
        warmth = gr / (gg + 1e-6)  # wheat ~ redder
        brightness = (gr + gg + gb) / 3
        crop = "wheat" if (warmth > 1.17 or brightness < 150) else "paddy"
        crop_conf = float(min(0.98, 0.6 + abs(warmth - 1.17) * 1.2 + grain_frac * 0.3))
    else:
        crop, crop_conf = "unknown", 0.0

    # foreign-matter boxes: 16x16 cell grid, group touching cells
    cell = 8
    gh = gw = 128 // cell
    grid = np.zeros((gh, gw), dtype=bool)
    for y in range(gh):
        for x in range(gw):
            grid[y, x] = foreign[y * cell:(y + 1) * cell, x * cell:(x + 1) * cell].mean() > 0.35
    seen = np.zeros_like(grid)
    detections = []
    for y in range(gh):
        for x in range(gw):
            if grid[y, x] and not seen[y, x]:
                stack, comp = [(y, x)], []
                seen[y, x] = True
                while stack:
                    cy, cx = stack.pop()
                    comp.append((cy, cx))
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < gh and 0 <= nx < gw and grid[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True
                            stack.append((ny, nx))
                ys, xs = [c[0] for c in comp], [c[1] for c in comp]
                detections.append(
                    {
                        "label": "foreign_matter",
                        "conf": round(min(0.97, 0.7 + len(comp) * 0.02), 3),
                        "box": [min(xs) / gw, min(ys) / gh, (max(xs) - min(xs) + 1) / gw, (max(ys) - min(ys) + 1) / gh],
                    }
                )
    return {
        "engine": "colour-heuristic fallback (swap in fine-tuned YOLOv8)",
        "crop": crop,
        "crop_confidence": round(crop_conf, 3),
        "grain_fraction": round(grain_frac, 4),
        "foreign_fraction": round(foreign_frac, 4),
        "detections": detections,
    }


def assay(img: Image.Image) -> dict:
    out = _heuristic_assay(img)
    yolo = _try_yolo(img)
    if yolo:
        out["engine"] = yolo["engine"] + " + heuristic crop classifier"
        out["detections"] = yolo["detections"] or out["detections"]
    return out


# --------------------------------------------------------------------------- pipeline
class ProcureRequest(BaseModel):
    card_id: str
    finger: str = "enrolled"  # "enrolled" | "stranger"
    declared_crop: str = "wheat"
    true_weight_kg: float = 50.0  # what is physically on the scale
    image_b64: Optional[str] = None
    # attack knobs for the Threat Lab
    forged_weight_kg: Optional[float] = None  # attacker edits payload after the scale signed it
    scale_unplugged: bool = False
    camera_covered: bool = False


def step(name: str, ok: bool, detail: str, extra: Optional[dict] = None) -> dict:
    return {"name": name, "ok": ok, "detail": detail, **(extra or {})}


@app.post("/api/procure")
def procure(req: ProcureRequest):
    steps: list[dict] = []
    halted_reason: Optional[str] = None

    # 1. Identity (Match-on-Card)
    ident = match_on_card(req.card_id, req.finger)
    steps.append(step("Identity (Match-on-Card)", ident["match"], ident["reason"]))
    farmer = FARMERS.get(req.card_id)

    # 2. Fail-secure hardware checks
    if req.scale_unplugged:
        steps.append(step("Scale heartbeat", False, "Scale offline, system halted (no manual override)"))
        halted_reason = "scale_unplugged"
    if req.camera_covered:
        steps.append(step("Camera heartbeat", False, "Camera blocked, system halted (no manual override)"))
        halted_reason = halted_reason or "camera_covered"

    # 3. Scale attestation (signed at the device)
    scale_payload = {
        "device": "SCALE-ESP32-0001",
        "card_id": req.card_id,
        "weight_kg": round(req.true_weight_kg, 2),
        "nonce": uuid.uuid4().hex[:12],
        "ts": int(time.time()),
    }
    scale_sig = sign("SCALE-ESP32-0001", scale_payload)
    submitted = dict(scale_payload)
    if req.forged_weight_kg is not None:
        submitted["weight_kg"] = round(req.forged_weight_kg, 2)  # attacker edits in transit
    sig_ok = verify("SCALE-ESP32-0001", submitted, scale_sig)
    in_range = WEIGHT_LIMITS_KG[0] <= submitted["weight_kg"] <= WEIGHT_LIMITS_KG[1]
    if not req.scale_unplugged:
        steps.append(
            step(
                "Scale attestation (ECDSA)",
                sig_ok and in_range,
                "Signature valid, weight %.2f kg" % submitted["weight_kg"]
                if sig_ok and in_range
                else ("Signature INVALID: payload altered after signing" if not sig_ok else "Weight outside plausible range"),
                {"signature": scale_sig[:32] + "...", "payload": submitted},
            )
        )

    # 4. Vision assay
    vision = None
    if not req.camera_covered:
        if req.image_b64:
            vision = assay(decode_image(req.image_b64))
        else:
            vision = {"engine": "none", "crop": "unknown", "crop_confidence": 0, "foreign_fraction": 0, "detections": []}
        vision_payload = {
            "device": "VISION-PI5-0001",
            "crop": vision["crop"],
            "foreign_fraction": vision["foreign_fraction"],
            "image_sha256": hashlib.sha256((req.image_b64 or "").encode()).hexdigest(),
            "ts": int(time.time()),
        }
        vision_sig = sign("VISION-PI5-0001", vision_payload)
        v_sig_ok = verify("VISION-PI5-0001", vision_payload, vision_sig)
        clean = vision["foreign_fraction"] <= FOREIGN_MATTER_LIMIT
        crop_match = vision["crop"] == req.declared_crop
        steps.append(
            step(
                "Vision assay (YOLOv8 node)",
                v_sig_ok and clean and crop_match,
                (
                    "Crop %s matches declared, no foreign matter" % vision["crop"]
                    if clean and crop_match
                    else (
                        "Foreign matter %.1f%% exceeds %.0f%% limit" % (vision["foreign_fraction"] * 100, FOREIGN_MATTER_LIMIT * 100)
                        if not clean
                        else "Sack looks like %s but %s was declared" % (vision["crop"], req.declared_crop)
                    )
                ),
                {"vision": vision},
            )
        )

    # 5. Consensus (3-of-3)
    votes = {
        "identity": bool(ident["match"]),
        "scale": bool(not req.scale_unplugged and sig_ok and in_range),
        "vision": bool(
            vision is not None
            and v_sig_ok
            and vision["foreign_fraction"] <= FOREIGN_MATTER_LIMIT
            and vision["crop"] == req.declared_crop
        ),
    }
    approved = all(votes.values()) and halted_reason is None
    steps.append(
        step(
            "Consensus (3-of-3 multi-sig)",
            approved,
            "All three oracles agree: escrow released" if approved else "Consensus failed (%d/3 votes), funds stay locked" % sum(votes.values()),
            {"votes": votes},
        )
    )

    # 6. Escrow payout + ledger
    payout = 0.0
    block = None
    if approved:
        rate = MSP_PER_QUINTAL[req.declared_crop]
        payout = round(submitted["weight_kg"] / 100.0 * rate, 2)
        block = append_block(
            "procurement",
            {
                "farmer": farmer["name"],
                "wallet": farmer["wallet"],
                "card_id": req.card_id,
                "crop": req.declared_crop,
                "weight_kg": submitted["weight_kg"],
                "msp_per_quintal": rate,
                "payout_inr": payout,
                "scale_sig": scale_sig,
                "vision_image_sha256": vision_payload["image_sha256"],
                "ipfs_cid_sim": "bafy" + vision_payload["image_sha256"][:40],
                "votes": votes,
            },
        )
        steps.append(step("Escrow payout", True, "Rs %.2f sent to %s" % (payout, farmer["wallet"]), {"payout": payout}))
    else:
        block = append_block(
            "rejected",
            {
                "card_id": req.card_id,
                "declared_crop": req.declared_crop,
                "votes": votes,
                "halted": halted_reason,
                "reasons": [s["detail"] for s in steps if not s["ok"]],
            },
        )
        steps.append(step("Escrow payout", False, "No funds released"))

    return {
        "approved": approved,
        "payout_inr": payout,
        "farmer": farmer,
        "steps": steps,
        "block": block,
        "vision": vision,
    }


# --------------------------------------------------------------------------- misc routes
@app.get("/api/state")
def state():
    paid = sum(b["data"].get("payout_inr", 0) for b in LEDGER if b["kind"] == "procurement")
    return {
        "devices": DEVICE_PUBKEYS,
        "farmers": FARMERS,
        "msp": MSP_PER_QUINTAL,
        "ledger": LEDGER,
        "chain": verify_chain(),
        "totals": {
            "accepted": sum(1 for b in LEDGER if b["kind"] == "procurement"),
            "rejected": sum(1 for b in LEDGER if b["kind"] == "rejected"),
            "disbursed_inr": round(paid, 2),
            "kg_procured": round(sum(b["data"].get("weight_kg", 0) for b in LEDGER if b["kind"] == "procurement"), 2),
        },
    }


@app.post("/api/ledger/tamper/{height}")
def tamper(height: int):
    """Demo only: silently edit a past block to show that the chain detects it."""
    if height <= 0 or height >= len(LEDGER):
        raise HTTPException(400, "Pick a block after genesis")
    d = LEDGER[height]["data"]
    if "weight_kg" in d:
        d["weight_kg"] = round(d["weight_kg"] * 0.9, 2)  # the classic 10% shortchange
    else:
        d["tampered"] = True
    return verify_chain()


@app.post("/api/ledger/reset")
def reset():
    LEDGER.clear()
    append_block("genesis", {"note": "DPOP prototype chain started", "devices": DEVICE_PUBKEYS})
    return {"ok": True}


@app.get("/api/health")
def health():
    return {"ok": True}


# --------------------------------------------------------------------------- demo scenes
from fastapi.responses import Response  # noqa: E402

SCENES = {
    "clean_wheat": "Clean wheat sack",
    "clean_paddy": "Clean paddy sack",
    "wheat_with_stones": "Wheat with stones and dirt added",
    "sand_fake": "Sand weighed as grain",
}


def make_scene(name: str, size: int = 512, seed: int = 7) -> Image.Image:
    rng = np.random.default_rng(seed + sum(map(ord, name)))
    img = np.zeros((size, size, 3), dtype=np.float32)
    img[:] = (38, 34, 30)  # dark sack-mouth background

    yy, xx = np.mgrid[0:size, 0:size]
    cx = cy = size / 2
    inside = ((xx - cx) ** 2 + (yy - cy) ** 2) < (size * 0.45) ** 2

    def grain_layer(base):
        noise = rng.normal(0, 14, (size, size, 1))
        speck = rng.random((size, size, 1)) < 0.08
        col = np.array(base, dtype=np.float32) + noise
        col = np.where(speck, col * 0.78, col)
        return np.clip(col, 0, 255)

    if name == "clean_wheat":
        img[inside] = grain_layer((176, 124, 64))[inside]
    elif name == "clean_paddy":
        img[inside] = grain_layer((222, 192, 110))[inside]
    elif name == "wheat_with_stones":
        img[inside] = grain_layer((176, 124, 64))[inside]
        for _ in range(7):
            sx, sy = rng.integers(int(size * 0.25), int(size * 0.75), 2)
            rad = int(rng.integers(14, 26))
            m = ((xx - sx) ** 2 + (yy - sy) ** 2) < rad ** 2
            tone = rng.integers(100, 140)
            img[m] = (tone, tone, tone + 4) + rng.normal(0, 6, (int(m.sum()), 3))
        for _ in range(3):
            sx, sy = rng.integers(int(size * 0.25), int(size * 0.75), 2)
            rad = int(rng.integers(20, 30))
            m = ((xx - sx) ** 2 + (yy - sy) ** 2) < rad ** 2
            img[m] = (52, 40, 30) + rng.normal(0, 6, (int(m.sum()), 3))
    elif name == "sand_fake":
        img[inside] = grain_layer((150, 142, 130))[inside]
    else:
        raise HTTPException(404, "Unknown scene")
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


@app.get("/api/scenes")
def scenes():
    return SCENES


@app.get("/api/scene/{name}.png")
def scene_png(name: str):
    buf = io.BytesIO()
    make_scene(name).save(buf, format="PNG")
    return Response(buf.getvalue(), media_type="image/png")
