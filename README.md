# DPOP: Decentralized Proof-of-Procurement

> **Smart India Hackathon 2026 | Problem Statement: PS26211**
> **Team:** The W.A.L.L. | **Category:** Hardware
> **👀 Live Demo:** [![Deployed on Vercel](https://img.shields.io/badge/Deployed_on-Vercel-black?style=for-the-badge&logo=vercel)](https://sih-26211.vercel.app/)

[![React](https://img.shields.io/badge/Frontend-React-blue?style=flat-square&logo=react)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Solidity](https://img.shields.io/badge/Web3-Solidity-363636?style=flat-square&logo=solidity)](https://soliditylang.org/)
[![Hardware](https://img.shields.io/badge/IoT-ESP32%20%7C%20Raspberry%20Pi-E34F26?style=flat-square)](https://www.espressif.com/)
[![AI](https://img.shields.io/badge/Edge%20AI-YOLOv8-FF9D00?style=flat-square)](https://ultralytics.com/)

**DPOP** is an autonomous, AI and IoT-powered blockchain bridge that physically eliminates the middleman and guarantees 100% transparent agricultural procurement. 

By replacing human data entry with cryptographically signed hardware telemetry, DPOP solves the Web3 "Oracle Problem" and creates a **Zero-Trust, Zero-Babu** payment gateway for Indian farmers.

---

## 🚨 The Problem: Fraud in APMC marketplace
Despite digital portals like e-NAM, government procurement relies entirely on manual data entry, creating massive corruption loopholes:
1. **Identity Hijacking:** Middlemen use proxy identities to steal MSP (Minimum Support Price) funds.
2. **Weight & Moisture Fraud:** Corrupt officials manually type lower weights; farmers spray crops with water to artificially inflate weight.
3. **Subjective Grading:** Inspectors arbitrarily downgrade crop quality to demand bribes.
4. **The "Oracle Flaw":** *Garbage In, Garbage Out.* If an official types a lie, the database securely records a lie.

---

## 💡 Our Solution: 3-of-3 Hardware Consensus
DPOP replaces the keyboard with physical sensors. A payout is only triggered when three independent hardware nodes reach consensus on-chain:

1. 🪪 **Sovereign Identity (Offline):** A 100% offline Match-on-Card biometric scan via an NFC Smart Card authenticates the farmer without biometric data ever leaving the chip.
2. ⚖️ **IoT Telemetry (Cryptographic Scale):** An ESP32 reads the HX711 Load Cell (Weight). The payload is encrypted at the silicon level using hardware private keys.
3. 👁️ **Edge AI Assayer (Vision):** A local Raspberry Pi running YOLOv8 inspects the open grain sack in real-time, detecting foreign objects (stones/dirt) and pushing a permanent forensic photo to IPFS.

**Result:** If Identity is Valid + Weight/Moisture is Confirmed + AI detects no rocks ➡️ **The Smart Contract automatically pays the farmer.**

---

## ⚙️ Tech Stack & Architecture

### Hardware & Edge (The Oracles)
* **Microcontroller:** ESP32-WROOM
* **Sensors:** HX711 Load Cell ADC
* **Identity:** PN532 NFC Module 
* **Edge AI Node:** Raspberry Pi 5 + 1080p Webcam

### AI & Backend
* **Computer Vision:** PyTorch, Ultralytics YOLOv8 (Local Inference), OpenCV
* **Middleware:** FastAPI (Python), Web3.py
* **Decentralized Storage:** IPFS / Pinata (For forensic photo evidence)

### Web3 & Frontend
* **Smart Contracts:** Solidity
* **Network:** Polygon (Layer 2) / Hyperledger Fabric 
* **Gasless Execution:** Biconomy Relayers (EIP-2771) -> *Farmers pay zero gas fees.*
* **UI Dashboard:** React.js, Tailwind CSS, Lucide Icons

---

## 🚀 How to Run the Local Prototype

This repository contains the hackathon prototype. It simulates the hardware telemetry and runs the local AI assayer.

### 1. Clone the Repo
```bash
git clone https://github.com/your-username/dpop-sih.git
cd dpop-sih
