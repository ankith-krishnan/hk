# Three-minute LocalRecall demo

This script is ready for rehearsal once real Qwen image inference, the manual backend path, and a WAN-off/LAN-on run have been verified. Do not replace the measured-results line with estimates.

## 0:00–0:35 · Member 1 — problem and privacy

“People forget where they put everyday objects. A continuously cloud-connected camera can create a record, but it also sends private room imagery away. LocalRecall is designed for one bounded workspace and stores semantic events with evidence rather than continuous application video.”

## 0:35–1:35 · Member 2 — product interaction

1. Show the local/offline status and the laptop browser connected through the SSH localhost forward.
2. Open **Watch** and load three zones and an enrolled object if the database is empty.
3. Use the upload/snapshot fallback: choose BEFORE and AFTER images showing one clear move, then select **Analyze Change**.
4. Open the event evidence and visible observations.
5. Ask “Where are my keys?” and show the cited event ID and evidence.

If the laptop camera or stream is unavailable, use the uploaded pair. The server itself has no camera. Do not present the current ingress-only stream as automatic recognition.

## 1:35–2:25 · Member 3 — architecture

“OpenCV is the inexpensive change gate for future Watch Mode. Qwen3.8-27B-NVFP4 analyzes a labeled BEFORE/AFTER composite locally. Pydantic validates its JSON, unknown IDs are rejected, and low-confidence results do not update location. SQLite is the factual memory and its current-state projection can be rebuilt from accepted events.”

Show that the configured model endpoint is loopback and that the laptop-to-GB10 LAN/SSH link remains active while external WAN is unavailable. State that frames do traverse the private local connection.

## 2:25–3:00 · Member 1 — measured result and close

“On the evaluated device, the measured [trial count] trials achieved [measured event precision/recall] and [measured median model / end-to-end latency]. These are results from our recorded trials, not estimates.”

If measurements or the offline demonstration have not been run, say that those results are not measured and use the fallback uploaded pair. End by showing Delete All Memory and explaining that transient Gradio cache files are explicitly managed rather than described as nonexistent.
