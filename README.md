# TheAnalyst

A small Flask web app to upload files and save them to an `uploads/` folder. The project uses a virtual environment for dependencies.

## What it contains
- `main.py` — Flask application with `/` (index) and `/upload` routes.
- `templates/index.html` — HTML form (already present in the workspace).
- `requirements.txt` — pinned dependencies for the project.
- `.venv/` — project virtual environment (created locally).

## Setup (Windows PowerShell)
1. Create the venv (already created by the project helper):

   ```powershell
   C:/Python314/python.exe -m venv .venv
   ```

2. Activate the venv:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

## Run the app
With the venv activated, run:

```powershell
python main.py
```

Then open a browser at `http://127.0.0.1:5000/`.

Notes:
- If VS Code doesn't resolve imports, select the interpreter `./.venv/Scripts/python.exe` (Ctrl+Shift+P → "Python: Select Interpreter") or reload the window.
- `.venv/` is added to `.gitignore`.

## Troubleshooting
- If the server doesn't start, check `flask.log` and `flask.err` in the project root for captured logs (the helper may redirect output there).
- To run without Flask's reloader (useful for debugging), run:

```powershell
python -c "from main import app; app.run(debug=False)"
```

If you want, I can remove the `debug=True` reloader from `main.py` (so `python main.py` runs in a single process), or add a small test script to programmatically verify the server. Let me know which you prefer.
