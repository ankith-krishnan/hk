# LocalRecall Headless Camera Runbook

**Applies to:** single Ubuntu 24.04 DGX Spark / ASUS GX10-class server with no camera and no monitor attached; one presenter laptop running a browser with an optional webcam. No cloud model or public Gradio sharing.

## 1. Architecture and priority order

```text
PRESENTER LAPTOP
  Browser webcam / webcam snapshots / uploaded image pair
  http://127.0.0.1:7860  (SSH port-forward, camera-permitted origin)
        |
        | encrypted SSH over LOCAL LAN (or private cable)
        v
HEADLESS SPARK
  Gradio Blocks: 127.0.0.1:7860
  FrameSource: BrowserPushSource / ManualPairSource / FixtureSource
  Motion worker: OpenCV (browser frames only)
  Qwen3.8-27B-NVFP4: 127.0.0.1:8000 (local VLM)
  SQLite and evidence: local disk
```

P0: take or upload separate BEFORE/AFTER images in browser -> Analyze -> SQLite -> Ask -> Evidence. No live camera dependency.

P1: a browser webcam live input streams about two RGB frames per second to a bounded RAM ring; OpenCV detects settled changes and enqueues at most one VLM inference at a time.

P2: optional prerecorded video upload/replay, better camera controls, richer review interactions.

## 2. Safe startup (commands run by the TECHNICAL member)

On **Spark**:

```bash
# In the repository on the Spark, after Codex has implemented the scripts:
./scripts/start_vllm.sh
./scripts/wait_for_vllm.sh

# Gradio must listen on Spark localhost, not public 0.0.0.0:
python -m app.ui.app --backend --host 127.0.0.1 --port 7860
```

On the **PRESENTER LAPTOP** (new terminal; not on Spark):

```bash
# Replace with actual private/LAN Spark address and SSH user.
ssh -N -L 7860:127.0.0.1:7860 <spark-user>@<spark-lan-ip>
```

On that laptop, open **Chrome/Firefox**:

```text
http://127.0.0.1:7860
```

Allow access to the **LAPTOP camera** when the browser asks. Nothing needs to exist at `/dev/video0` on the Spark. The SSH command stays running while the browser is open. You may use an existing SSH connection with `-L`, or VS Code port forwarding, provided the resulting browser URL is local to the laptop. Do not run Gradio with `share=True` and do not put the model API on a public interface.

**Important:** A plain `http://<spark-ip>:7860` LAN URL is usually NOT a browser secure context, so the webcam may be unavailable. `http://localhost` / `http://127.0.0.1` reached through SSH forwarding is the simplest reliable method; HTTPS is another option but not required for this demo.

## 3. Preflight in this exact order

1. `nvidia-smi`; verify model startup and a one-image multimodal smoke test.
2. Start mock Gradio, open the laptop browser, test BEFORE/AFTER **file upload** from local images (works with no webcam permission).
3. Test browser webcam snapshots in the two non-streaming Gradio image inputs, if the laptop has a camera. Webcam access is browser controlled.
4. Verify manual `facade.analyze_pair` returns a real event, persists it, and `Where are my keys?` cites that event.
5. ONLY NOW test `gr.Image(sources=["webcam"], streaming=True)` and show `frames_received` / last-frame-age status.
6. Move an object with a stable camera angle and test OpenCV trigger. If unreliable, leave manual mode as the judged demo.
7. Stop the stream, close the browser tab, wait >4 seconds, and verify status becomes `Camera disconnected`, while Ask and manual upload still work.
8. Confirm three teammates can each explain the client (browser), backend (Spark), and database division.

## 4. Gradio event wiring

Use two distinct image input components. A single streaming `gr.Image` cannot simultaneously have `sources=["webcam", "upload"]` in tested Gradio APIs. Manual image inputs MUST be nonstreaming.

```python
# Example wiring to be adapted to the installed, pinned Gradio release.
with gr.Blocks() as demo:
    before = gr.Image(label="BEFORE (webcam snapshot or file)",
                      sources=["webcam", "upload"], type="numpy")
    after = gr.Image(label="AFTER (webcam snapshot or file)",
                     sources=["webcam", "upload"], type="numpy")
    analyze = gr.Button("Analyze Change")
    result = gr.JSON()
    analyze.click(fn=callbacks.analyze_pair, inputs=[before, after],
                  outputs=[result], queue=True)  # queued: model call is slow

    browser_camera = gr.Image(label="Live laptop webcam (optional)",
                              sources=["webcam"], type="numpy", streaming=True)
    # A per-browser token in gr.State may be supplied as a second input.
    browser_camera.stream(fn=callbacks.ingest_browser_frame,
                          inputs=[browser_camera, browser_source_id],
                          outputs=[ingest_status], stream_every=0.5,
                          time_limit=60, queue=False)
```

`browser_source_id` and `ingest_status` are Gradio components to define in the real app; this is an API-shape illustration, not a complete standalone module. Camera preview is the browser's `browser_camera` input; the server does not need to return a preview frame on every timer tick. Timer polling is only for health, memory, and evidence.

Ingest handler requirements: validate `RGB uint8 HxWx3`; resize to a bounded maximum; copy into ring buffer with a monotonic receive timestamp; immediately return. Do NOT run VLM inference, write DB events, or process heavy video inside `.stream()`. Inference happens in a separate single-worker queue after the motion state machine settles.

## 5. Offline and privacy truthfulness

- All model calls go to `127.0.0.1:8000`; events and evidence are stored on Spark. The presenter laptop and Spark can talk over LAN with NO external internet. **Do not switch off the only Wi-Fi/Ethernet network supporting SSH.**
- Do not claim that frames never cross any network: they do traverse the local connection (encrypted if via SSH). Do not claim zero temporary files: Gradio may cache webcam uploads. Set and periodically prune a dedicated `GRADIO_TEMP_DIR`, preferably on adequately sized volatile storage when suitable; verify behavior with the installed Gradio version.
- Gradio `share=False`; bind 127.0.0.1; no CDN/analytics/cloud endpoints. Validate settings in UI, not with a decorative OFFLINE badge.
- Keep only registered references and BEFORE/AFTER event evidence long term. Wipe session cache and retained evidence on Delete All Memory as documented; do not delete model caches or fixture assets.
- To prove independence from WAN, prefer a local Ethernet/LAN and show blocked/unavailable external model access while the local browser connection is still operational. Never use host firewall changes that could lock the team out of the Spark.

## 6. Failure modes, immediate actions

| Symptom | Explanation | Immediate fallback |
| --- | --- | --- |
| No `video0` on Spark | Expected: headless host has no camera | Continue; upload image pair in browser |
| Browser never prompts for camera | Missing laptop camera, browser denied permission, non-secure origin | Open `http://127.0.0.1:7860` via SSH tunnel; or upload images |
| Webcam preview works but ingestion count stays 0 | `.stream` not active, callback error, stream listener busy | Inspect UI status/Gradio logs; use manual image pair |
| Live capture stops when tab sleeps/closes | Browser owns the stream | Reopen/permit browser stream or use manual upload |
| Frame age >4s | Source is stale | Auto Watch pauses; manual mode remains operational |
| Webcam zones are reversed | Browser mirrors selfie camera | Use nonmirrored view or recalibrate zones for actual received image |
| Wi-Fi disconnected and UI disappears | Lost the SSH/LAN path, not a model failure | Restore local link; prove offline by disabling WAN only |
| Camera unavailable at event | No presenter camera/permissions | Two uploaded still images or prerecorded fixture video |
| Model serves text but not image | Runtime/processor mismatch | Switch documented inference backend or local VLM, keeping same facade |

## 7. Freeze rules and acceptance gates

- **Gate A:** Qwen multimodal text/image smoke test works on Spark; otherwise debug runtime before camera work.
- **Gate B (P0):** manual two-image upload on laptop browser -> Qwen -> validated event -> SQLite -> Ask + evidence, with no camera plugged into Spark.
- **Gate C (P1):** optional browser webcam `.stream` with timestamped source health, meaningful motion trigger, duplicate suppression; if flaky, leave disabled.
- **Gate D:** LAN/SSH is stable, public sharing disabled, external cloud access unnecessary, measured demo metrics and backup image/video evidence ready.

**No teammate is required to SSH.** The technical owner configures the environment and tunnel. Everyone else can work on Gradio/fixtures in already-open browser/Codex sessions.
