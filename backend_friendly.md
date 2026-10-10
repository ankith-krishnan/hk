# Backend directions for beginners

This guide is for two people who are newer to backend programming. You can share the backend work without each person having to learn every part of LocalRecall. One person handles **getting the local model to answer**. The other handles **connecting answers to the app’s saved memory**. Agree on the small handoff points below before editing files.

The word “backend” can sound mysterious. Here it means the Python code behind the page: it receives pictures and questions, asks the local model for help, checks the model’s answer, and saves useful facts. The Gradio page is the front counter. The backend is the room behind the counter where the work happens.

## Read this first

There is already a backend starter project. You are improving it, not starting from an empty folder. Read these in order:

1. `README.md` — what the app is supposed to do.
2. `ARCHITECTURE.md` — the picture of how its parts connect.
3. `RUNBOOK.md` — the commands an operator uses.
4. `app/contracts.py` — the list of things the Gradio page can ask the backend to do.
5. This guide, then the longer technical guide in `BACKEND.md` if you need more detail.

The current most important path is **manual image pair**: provide a BEFORE picture and an AFTER picture, analyze them locally, save the result, and ask where an object is. Automatic camera event detection is not ready. Leave it off while you work on the manual path.

## The two backend jobs

### Backend Friend 1: local model setup and answer checking

Own the goal “a picture goes to the local model and a safe, structured answer comes back.” Work mainly in:

- `scripts/start_vllm.sh`
- `scripts/wait_for_vllm.sh`
- `scripts/stop_vllm.sh`
- `scripts/smoke_text.py`
- `scripts/smoke_vision.py`
- `app/vlm_client.py`
- `app/event_analyzer.py`
- `app/prompts/`

The order is important: first prove the vLLM server works by itself, then prove that the Python client can talk to it, and only then connect it to the rest of the app. This way, if something breaks, you know which piece to investigate.

### Backend Friend 2: saved memory and app connection

Own the goal “a checked answer becomes a saved fact the app can show and query.” Work mainly in:

- `app/facade.py`
- `app/memory_store.py`
- `app/query_service.py`
- `app/schemas.py`
- `app/privacy.py`
- backend tests under `tests/`

The order is: understand the shared function list, use the mock model to test manual analysis, make sure SQLite stores and returns correct events, and then use the real model client once Friend 1 has passed the image test.

If only one of you can edit a file at a time, that is normal. Do not both edit the same file in different places and then try to paste changes together. Tell each other when you start and finish a shared file.

## A few words in plain English

- **Function:** a named action in Python. For example, `ask()` is the action that answers a question.
- **Input:** information given to a function, like the BEFORE and AFTER pictures.
- **Return value:** information the function gives back, like an event record.
- **Facade:** one simple doorway that the page uses to ask the backend for work. It keeps the page from needing to know about databases or models.
- **Model client:** code that sends a request to Qwen and reads its reply.
- **Schema:** a set of rules for what a valid answer must look like.
- **SQLite:** a small database saved as a local file. It keeps the event history after the program closes.
- **Mock:** a pretend model with predictable fixture answers. It helps you test your own code before Qwen is available. A mock answer is never proof that Qwen worked.
- **Loopback / localhost:** an address that points back to this same computer. LocalRecall uses it so model requests stay on the GB10.

## Shared setup

The repository’s `main` folder currently has uncommitted changes. Nobody should erase them. Before splitting into work areas, ask the person integrating the project to make a checkpoint commit. A commit is a saved point you can return to if an experiment goes wrong.

Once the checkpoint exists, each person should use a separate worktree. A worktree is a second folder for the same Git project, so people can work at the same time without editing the same copy.

For example, the integrator can create these folders:

```bash
git worktree add ../localrecall-backend-model -b feature/backend-model <checkpoint-commit>
git worktree add ../localrecall-backend-memory -b feature/backend-memory <checkpoint-commit>
```

Each person then enters their own folder and runs:

```bash
make setup
make test
make lint
```

If you see a test failure before you change any code, tell the integrator and copy the full error text. Do not hide it by deleting the test.

## Backend Friend 1: model setup, one step at a time

### Step 1: Check whether Docker works for your account

Run:

```bash
sudo -n docker info
```

This machine currently needs `sudo -n docker`. If that command fails or asks for a password, stop and ask the computer’s owner for help. This is an account permission issue, not a Python bug. Do not edit the socket permissions, add users to groups, or use someone else’s password.

### Step 2: Finish the model download

The model is named `nvidia/Qwen3.8-27B-NVFP4`. It is large, about 21.9 GB from the initial download estimate. Check free disk space before starting:

```bash
df -h "$HOME"
du -sh "$HOME/.cache/huggingface/hub" 2>/dev/null || true
```

Do not download the weights into the regular host Hugging Face cache. The project launcher will download the model from inside the vLLM container into a persistent Docker volume named `localrecall-qwen38-cache`. This keeps the weights separate from the vLLM runtime image. If a download is interrupted, rerun `./scripts/start_vllm.sh`; it should reuse the Docker volume and resume from cached files.

### Step 3: Start the server

Run:

```bash
./scripts/start_vllm.sh
./scripts/wait_for_vllm.sh
```

The first command pulls the runtime if needed, downloads/verifies the weights in the Docker volume, checks vLLM's supported options, and starts the serving container. The second waits for the server to answer. If the command fails, copy the last 30 lines of the error and container log for the integrator. Do not remove an existing container or model volume unless the team has checked why it is there.

### Step 4: Ask for text, then an image

Run:

```bash
make model-smoke
```

Read the result carefully:

- Text success means the model answered a text request.
- Image success means it accepted and answered the synthetic image request.
- Both must pass before anyone says that image inference works.

The fake local mock server is useful for checking request formatting, but its answers are written by the project. Never call that a Qwen test.

### Step 5: Tell Friend 2 exactly what passed

Send the Backend Friend 2 and integrator:

- the command you ran;
- whether text passed;
- whether image passed;
- the reported model name;
- latency as printed by the tool;
- any error text.

Do not change `LocalRecallFacade` methods to pass model information. The `VLMClient` is the agreed place for model-specific work.

## Backend Friend 2: memory and app connection, one step at a time

### Step 1: Look at the shared function list

Open `app/contracts.py`. It lists functions such as `analyze_pair`, `ask`, `enroll_object`, and `get_events`. The Gradio page calls those functions. Keep their names and returned information stable so the frontend teammates do not have to rewrite their screens.

If a function truly needs another input or output, write down why and discuss it with Friend 1 and both frontend people **before** changing `app/contracts.py`.

### Step 2: Prove storage with the fake model

Run:

```bash
make test
```

The tests create temporary SQLite files so they do not erase anyone’s actual memory. Read `tests/test_memory_store.py` to see examples. Check that:

- an event can be saved and read back;
- accepted moves update the current location;
- rejected or uncertain events do not change the location;
- correcting an event rebuilds the current location;
- a query answer can point back to the event that supports it.

Do not ask a model to remember facts. SQLite is the memory; the model only describes what it sees.

### Step 3: Trace one manual analysis through the code

Follow this path in the editor:

```text
Gradio Analyze button
    → app/ui/callbacks.py
    → app/contracts.py method name
    → app/facade.py
    → app/event_analyzer.py
    → app/vlm_client.py
    → validated result
    → app/memory_store.py
    → app/query_service.py
```

You do not need to change every file. The point is to understand where each part belongs. The callback should not contain SQL. The memory store should not make HTTP requests. The facade connects the parts.

### Step 4: Check privacy and file handling

Use a temporary test directory, never a real personal photo, while testing deletion. Confirm the app keeps transient Gradio files under the configured temp folder, removes old files, and clears them after a confirmed Delete All action or normal shutdown. Event evidence is different from temporary upload files: saved event evidence is meant to remain until the user deletes memory.

The app does not currently write a continuous video file. Do not claim that no image file is ever stored; the app saves explicit evidence and Gradio can use temporary upload files.

### Step 5: Connect the real model only after Friend 1’s handoff

When Friend 1 confirms that text **and image** smoke tests passed, launch the app in backend mode:

```bash
.venv/bin/python -m app.ui.app --backend --host 127.0.0.1 --port 7860
```

Load zones, enroll a demo object, provide a BEFORE/AFTER pair, inspect the saved event, and ask a question about the object. Check that the answer cites a saved event. If the model returns an invalid ID or uncertain answer, make sure the app does not silently move the object’s saved location.

## How to work together without mixing changes

At the start of each day, each person says which files they plan to change. If a change crosses your boundary, agree on it first. Examples:

- Friend 1 changes the model request or response format: tell Friend 2 before changing a schema.
- Friend 2 finds the facade needs a new function: discuss it with both frontend people before changing the contract.
- A frontend contributor needs a new result field: do not add it only in Gradio; agree on the contract and backend record first.

Before committing, check the files you changed:

```bash
git status --short
make test
make lint
```

Save your work with a clear message, for example:

```bash
git add app/vlm_client.py app/event_analyzer.py tests/test_event_pipeline_mock.py
git commit -m "verify structured local model responses"
```

Only stage your own files. Never add `.env`, `.venv`, model caches, private pictures, database files, or generated large videos.

## What counts as finished

### Friend 1 is finished when

- Docker can use the GPU from this account on the correct GB10 machine.
- The model files are complete and vLLM starts.
- Text smoke passes.
- Image smoke passes and raw output is saved.
- The exact results are recorded in `STATUS.md`.

### Friend 2 is finished when

- The manual pair works through the facade with mock inference.
- Event records, evidence paths, and current state survive a restart in a test database.
- Ask answers from stored records and points to supporting event evidence.
- Review, correction, delete, and privacy behavior pass tests.
- The backend still uses the agreed facade methods and the tests pass.

### The two of you are finished together when

- Friend 1’s real image client can be called by Friend 2’s facade without changing the Gradio contract.
- A person can run the real manual flow in the browser and see a saved event with evidence.
- Mock results and real Qwen results are clearly separated in the UI and documentation.
- Any feature that has not been tested is labeled “not verified” or “not measured.”

## If something goes wrong

1. Stop after the first clear error; do not keep changing random files.
2. Copy the command and complete error message.
3. Say whether you were running mock mode or real mode.
4. Say which file you last changed.
5. Ask the other backend friend or integrator to help identify the broken layer.

This is a normal way to debug software. Most problems become easier once the team knows whether they happened in Docker, the model request, the Python facade, SQLite, or the Gradio page.
