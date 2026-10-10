# Frontend A: Build the LocalRecall screens

## Your mission

You are responsible for how the app looks and how a person moves from one screen to another. You do **not** need to know how an AI model works. Think of the backend as a vending machine: you give it a request through an agreed button or function, and it gives you a result. Your job is to make those requests and results easy to understand.

The app is already built with **Gradio Blocks**, which lets Python describe a web page. The main file is `app/ui/app.py`. It already contains five tabs: **Watch**, **Memory**, **Ask**, **Setup**, and **System & Privacy**. Your job is to make that page clear, calm, and easy for a first-time user without changing what the backend promises to do.

## What you own

- `app/ui/app.py`: page layout, component labels, tab organization, button text, help text, and visual styling.
- Optional small styling changes in the CSS string inside that file.
- A short screenshot or written before/after note showing the improvement.

## What you should leave alone

- Do not put model calls, SQL statements, image analysis, or object-location rules in the UI file.
- Do not add JavaScript, React, another web server, a public Gradio share link, or a WebSocket system.
- Do not make Watch Mode look like automatic event detection. At the moment it only receives browser frames; automatic motion analysis is deliberately disabled.
- Do not remove the manual BEFORE/AFTER upload path. It is the main supported flow and must work even if there is no camera.
- Do not rename a function or change its inputs/outputs without telling Frontend B and the Backend owner first.

## First, understand the small amount of Gradio you need

Open `app/ui/app.py` and find this general pattern:

```python
with gr.Blocks() as demo:
    question = gr.Textbox(label="Ask a question")
    answer = gr.Markdown()
    ask_button = gr.Button("Ask")
    ask_button.click(run_ask, inputs=[question], outputs=[answer])
```

Read it as: “Put a text box on the page. Put an answer area on the page. When the button is clicked, call `run_ask` with the text box’s value, then put the returned value in the answer area.”

The main Gradio pieces used here are:

- `gr.Tabs()` and `gr.Tab("Name")`: separate the app into pages.
- `gr.Row()` and `gr.Column()`: place things side by side or stack them.
- `gr.Markdown()`: show headings and ordinary help text.
- `gr.Image()`: let the user upload or take a picture.
- `gr.Button()`: start an action.
- `gr.Dataframe()` and `gr.Gallery()`: show saved rows and pictures.
- `.click(...)`, `.submit(...)`, `.stream(...)`, and `.load(...)`: say what should happen after a user action or page event.

You do not have to memorize these names. Copy the style of nearby code and change one small section at a time.

## Set up your work area

The current `main` worktree has a committed scaffold plus additional uncommitted changes. **Do not run `git reset`, `git clean`, or discard those changes.** Ask the team integrator to make a safe checkpoint commit first. After that, work in your own branch/worktree so two people do not overwrite the same file.

From the project folder, the integrator can create your worktree with:

```bash
git worktree add ../localrecall-front-a -b feature/frontend-a <checkpoint-commit>
cd ../localrecall-front-a
```

Then install and run the mock UI:

```bash
make setup
make test
.venv/bin/python -m app.ui.app --mock --host 127.0.0.1 --port 7861
```

Open `http://127.0.0.1:7861` in a browser. Mock mode is safe for layout work. It uses fixture behavior and does not need the real model or Docker. It should say **MOCK** clearly.

## Build the screen in small steps

### 1. Sketch the path a new person should follow

Write down the path in one sentence before editing code:

1. Set up the object and zones.
2. Provide BEFORE and AFTER images.
3. Analyze the change.
4. Read the result and inspect its evidence.
5. Ask where the object is and see which event supports the answer.

The current tab names can stay. Improve the headings and helper text so the user knows what to do next. Use short words and one instruction at a time.

### 2. Make the important action easy to find

The Watch tab has two image boxes and an **Analyze Change** button. Make that button visually prominent. Put a short sentence above the image boxes, for example: “Add an earlier photo on the left and a later photo on the right.” Explain that either uploads or browser snapshots are acceptable.

Keep the two image labels explicit: **BEFORE** and **AFTER**. Do not call them “Image 1” and “Image 2”; order matters to the event result.

### 3. Explain the result plainly

After analysis, the page shows a short summary, structured event details, and an evidence gallery. Make sure those three outputs are visually grouped and labeled. A person should be able to answer:

- What does the system think happened?
- How sure is it?
- Which pictures support the answer?
- Does it need a human review?

Avoid showing a long block of raw JSON as the only explanation. The structured JSON can remain available as a secondary details panel.

### 4. Make other tabs easy to scan

- **Memory:** clearly label current object locations, recent events, and items awaiting review.
- **Ask:** show an example question such as “Where are my keys?” and a visible evidence area.
- **Setup:** explain the object name, aliases, reference photo, and zones with a small example.
- **System & Privacy:** say where frames travel, what is retained, and that temporary upload files can exist and are cleaned up.

Use friendly labels, but do not promise privacy behavior the app has not measured. For instance, say “No continuous video writer is enabled” rather than “Nothing is ever saved.”

### 5. Check narrow windows and errors

Open the browser at a normal laptop size and make the window narrower. Labels and buttons should still be understandable. Place related things together. If a component disappears below the fold, add an obvious heading so the user knows what is there.

Do not hide useful error messages. The UI wrappers turn exceptions into Gradio errors. Make sure the user can see them and recover, for example by adding the missing image or loading zones.

## How to change the page safely

1. Edit one tab or one group of labels.
2. Save the file.
3. Stop and restart the mock UI if it does not reload automatically.
4. Click through the affected part in the browser.
5. Check that the neighboring tabs still appear.
6. Run `make test` and `make lint`.
7. Ask Frontend B to check any component whose button callback you moved.
8. Commit only your UI file and any UI-only screenshots/notes.

Useful commands:

```bash
git status --short
make test
make lint
```

Before committing, `git status --short` should show the files you meant to change. Do not include `.env`, `.venv`, model files, event pictures, or the local SQLite database.

## Definition of done

- A first-time user can find the manual BEFORE/AFTER path without coaching.
- The page still has all five tabs.
- Mock mode is clearly labeled as mock.
- Camera streaming is described as optional and ingress-only; no automatic detection claim appears.
- Results show a plain-language summary and visible evidence.
- The page remains usable at laptop width and gives readable errors.
- `make test` and `make lint` pass.
- Frontend B and the integrator know exactly which UI labels or component positions changed.

## If you get stuck

Copy a nearby Gradio component pattern. Search the repository with:

```bash
rg "gr\.Tab|\.click\(|\.submit\(" app/ui
```

Ask the team before changing a function’s arguments or return values. That may be part of the shared bridge between the page and the backend.
