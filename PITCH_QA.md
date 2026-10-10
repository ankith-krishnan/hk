# Judge questions and answers

**Why not use a cloud API?**  The product is designed to keep image inference on the local GB10. The browser frames still travel over the private local laptop-to-server connection.

**Why Qwen3.8 NVFP4?**  It is the selected multimodal checkpoint and Spark recipe. We will claim image support only after the local image smoke test passes on this device.

**Why not run the VLM on every frame?**  That would spend compute and latency on unchanged scenes. The planned Watch Mode uses a cheap motion gate and invokes the VLM for candidate events; automatic detection is currently disabled.

**What happens when the model is wrong?**  Structured output is checked against enrolled IDs and zones. Confidence controls acceptance and review; the UI supports approval, rejection, and correction. Accepted state can be rebuilt from the event log.

**Is video stored?**  There is no continuous-video writer in the current path. Event/reference images and Gradio temporary cache files may be stored. Continuous-video persisted bytes have not been measured on a running real session.

**How can you prove local inference while WAN is disconnected?**  Keep the laptop-to-GB10 LAN/SSH route active, block only external WAN upstream access, and repeat the image request and query. This test has not yet been run.

**Why localhost/HTTPS for laptop camera access?**  Browsers restrict webcam capture to secure origins; localhost is treated as a trusted local origin. The SSH local forward gives the laptop a localhost URL. The server does not capture its own camera.

**What if the laptop tab closes?**  The browser frame source becomes stale and Watch Mode should stop. Manual uploads and saved-memory questions remain available.

**Why SQLite?**  It is local, transactional, simple to back up, and keeps an auditable event log separate from its rebuildable current-state projection.

**What are the limitations?**  Fixed bounded workspace, enrolled objects, named zones, occlusion and lighting sensitivity. Real Qwen image inference and real-world accuracy are not yet verified.

**What did each member build?**  State only confirmed contributions. The current worktree includes backend/UI, model-launch preparation, tests, and evaluation/demo materials; confirm individual ownership with the team.

**How would this scale beyond one desk?**  Add explicit workspaces and camera identities, partition event/evidence stores, and schedule independent local inference workers. Revisit retention, access control, and multi-user boundaries before broadening deployment.
