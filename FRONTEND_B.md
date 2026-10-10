# Frontend B: Make the buttons and screens work together

## Your mission

You own the user interactions: when someone clicks a button, the right function should run, and its answer should appear in the right place. You do not need to write the AI model or database. The Backend owner provides those through a Python interface called `LocalRecallFacade`.

Imagine a restaurant: the Gradio page is the menu, your callbacks are the waiter taking the order, and the facade is the kitchen. A callback should pass the order to the kitchen and bring the result back. It should not cook the meal itself.

The main files are:

- `app/ui/callbacks.py`: button helpers that call the facade.
- `app/ui/mock_facade.py`: fake answers and sample pictures for safe UI work.
- `app/ui/app.py`: the page wiring that connects a button to a callback.
- `tests/test_ui_contract.py` and other UI tests: checks that the interaction still fits together.

## Your responsibilities

- Make sure every visible button has a useful action and result message.
- Make manual BEFORE/AFTER analysis, Ask, setup, review, correction, export, and delete flows easy to test with mock data.
- Keep callback functions short. They check the user’s inputs, call the facade, and format the returned data.
- Explain errors in a way that helps the user fix the problem.
- Help test the optional browser webcam input, but do not make it required.

## Do not do these things

- Do not add model prompts, HTTP model requests, SQL, image-recognition rules, or camera hardware access to `app/ui/`.
- Do not add a new REST API, React app, JavaScript camera capture, WebSockets, or a public sharing URL.
- Do not call `cv2.VideoCapture(0)` or expect a camera to be plugged into the GB10. The camera is in the presenter’s laptop browser.
- Do not turn on automatic event detection. The current backend rejects Start Watch for real automatic analysis because that feature is not ready.
- Do not let mock UI changes change backend behavior. Mock mode is a visual/integration tool and must remain obviously marked `MOCK`.

## Learn the important bridge

Open `app/contracts.py`. It declares what functions the page can ask the backend to perform. For example:

```python
def analyze_pair(self, before: np.ndarray, after: np.ndarray) -> EventRecord: ...
def ask(self, question: str) -> QueryResult: ...
```

The page provides two images to `analyze_pair`, and the backend returns an `EventRecord`. The page sends a question to `ask`, and the backend returns a `QueryResult`. The callback must use the same names and information types. If something is missing, tell the Backend owner and agree on a change to `app/contracts.py` before you code around it.

Open `app/ui/callbacks.py` and read `analyze_pair()`. It checks that both pictures exist, calls `facade.analyze_pair(...)`, and returns a summary, details, and gallery pictures. That is the model to follow.

## Safe starting point

The current repository has uncommitted changes. Ask the integrator to save them in a checkpoint commit before making branches. Then get your own worktree:

```bash
git worktree add ../localrecall-front-b -b feature/frontend-b <checkpoint-commit>
cd ../localrecall-front-b
make setup
make test
```

Run the mock app on a port different from Frontend A’s port:

```bash
.venv/bin/python -m app.ui.app --mock --host 127.0.0.1 --port 7862
```

Open `http://127.0.0.1:7862`. This lets you check callbacks without Docker or a real model.

## Build and verify each interaction

### 1. Manual image pair

Find the **Analyze Change** button in `app/ui/app.py`. It is wired to `wrapped_analyze`, which calls `callbacks.analyze_pair` in `app/ui/callbacks.py`.

Check these cases:

- No BEFORE image: the user gets a short clear instruction.
- No AFTER image: same.
- Both images supplied: the result summary, details, and evidence gallery appear.
- Backend error: the page shows a recoverable error and does not pretend an event was saved.

Never analyze a pair from a browser polling timer. Only run model work when the person presses the button.

### 2. Ask and evidence

Check that the Ask button and pressing Enter both call the same callback. The answer should include the event number when available, and the gallery should show evidence for cited events. Do not invent evidence or make a mock answer sound like a real model result.

### 3. Setup actions

Check object enrollment, loading the three default zones, and saving a custom zone. If an image or required name is missing, show the person exactly what to supply. A callback should not silently ignore invalid input.

### 4. Review and correction

Check the pending review table, approval, rejection, and correction forms. A correction needs an event number and valid object/zone IDs. The backend validates the actual rules; the UI can make the choice easy, but must not pretend that text typed by a user is a valid ID without the backend checking it.

### 5. Delete and export

Delete All Memory must require the confirmation checkbox. Object deletion and zone disabling should say what they affect. Export should return a file the user can download. Try those actions only in mock mode or a disposable test database.

## Optional browser webcam input

The `gr.Image(..., sources=["webcam"], streaming=True)` component gets images from the user’s browser. Gradio sends them to the Python callback. The server stores only a bounded recent-frame ring in memory. The current callback reports that frames arrived; it does **not** detect moves or call the model.

For now, check only that:

- the page shows the browser camera control;
- browser permission can be granted when opened through localhost or a secure origin;
- the status says connected while frames arrive and disconnected after the browser stops;
- a laptop with no camera can still use image uploads.

Do not change the Start Watch button to say events are being detected until the Backend owner has implemented and verified that pipeline with a real local image model.

## A beginner-friendly debugging routine

When a button does nothing:

1. Look at the terminal running Gradio for a Python error.
2. Find the button in `app/ui/app.py` and note the callback name.
3. Find that callback in `app/ui/callbacks.py`.
4. Check that it receives the same inputs the button supplies.
5. Check that it returns the same number of values as the output components expect.
6. Reproduce it with mock mode before asking the Backend owner to investigate.

When the page displays the wrong value, follow the value backward: output component → callback return value → facade method result. Do not patch the UI to guess the database result.

Helpful commands:

```bash
rg "\.click\(|\.submit\(|def analyze_pair|def ask" app/ui
make test
make lint
```

## Definition of done

- Every visible button has a working, understandable response or a clear disabled/not-ready message.
- The manual pair and evidence flow works in mock mode without any camera.
- Errors are visible and explain the next action.
- Delete All Memory requires confirmation.
- Camera is optional and clearly belongs to the laptop browser.
- No model, database, or motion logic was added to UI callbacks.
- `make test` and `make lint` pass.
- The Backend owner has been told about any contract change before it is made.
