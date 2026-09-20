# CRPF Sentinel Mental Health & Stress Monitoring System (MHS) — Release v1.0.0

## 🛡️ Overview
Official production release of the **AI-powered Personnel Stress and Welfare Monitoring System** tailored for Central Armed Police Forces (CAPFs) and high-stress armed forces deployments.

This release packages the complete, fully offline, privacy-preserving multimodal AI architecture running locally on edge hardware via the **HKNT 1.0.4** binary neural format.

---

## 📦 Release Assets
1. **`CRPF_Sentinel_MHS_Mobile_v1.0.0.apk`** (21.4 MB)
   - Complete Android client with zero cloud AI dependencies.
   - On-device DistilBERT sequence risk classifier (6 clinical risk levels).
   - On-device Neural LLM for grounding and tactical resilience conversations.
   - On-device Whisper Base-EN automatic speech recognition (16kHz audio capture + 80-channel Log-Mel filterbank).
   - Offline Android Text-to-Speech (TTS) engine calibrated for military debrief delivery (0.92x cadence).
   - Account creation / registration endpoint and UI integrated directly into the APK.
   - Offline self-assessment journals and tactical resilience toolkit.

2. **`CRPF_Sentinel_Desktop.exe`** (6.18 MB standalone executable)
   - Windows desktop application with full CustomTkinter UI.
   - Hardware-accelerated HKNT 1.0.4 file encryption and decryption vault.
   - High-throughput text and image visual encryption pipelines.

3. **`CRPF_Sentinel_Desktop_v1.0.0_Windows.zip`** (32.7 MB)
   - Portable Windows distribution containing all runtime dependencies, Tkinter GUI backends, and cryptographic engines.

4. **`CRPF_Sentinel_Stress_Monitoring_System_Comprehensive_Report.pdf`** (15.5 KB)
   - Comprehensive technical, architectural, and governance report detailing the multi-tier system, HRMS metrics, biometrics, explainable AI (XAI), and zero-cloud privacy architecture.

---

## 🔬 Core Innovations & Highlights
- **HKNT 1.0.4 Unified Binary Standard**: 128-byte header alignment, strict `<4s H H I H H Q Q Q Q Q Q Q Q Q H 38s` packing, SIMD/AVX hardware compliance, zero-dependency serialization.
- **Multimodal On-Device Intelligence**:
  - DistilBERT 6-class triage: `NORMAL`, `MILD_STRESS`, `MODERATE_STRESS`, `HIGH_RISK`, `BURNOUT`, `CRISIS`.
  - Whisper Base-EN ASR: offline Mel-frequency speech feature extraction with live RMS microphone decibel metering.
  - Generative Neural LLM: causal attention scoring with military coping mechanisms.
  - Explainable AI (XAI): SHAP/LIME-style factor weighting and risk contributions.
- **Enterprise Enterprise & Cloud Resilience**:
  - FastAPI dual-route compatibility (`/api` and `/api/v1`).
  - Strict Pydantic v2 Settings management and PostgreSQL / SQLite dual-backend support.
  - Comprehensive unit test and integration suite with 100% test pass rate across JVM and Python test runners.
