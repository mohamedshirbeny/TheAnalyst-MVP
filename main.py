# Import necessary libraries: Flask for the web server, render_template to show html pages, and request to handle file uploads
# Also import os to handle file paths

# Create a Flask web server application

# Define the main route '/' which will display the index.html page

# Define the '/upload' route which will handle the file upload
# This route should only accept POST requests
# It should get the file from the request
# Check if a file was actually uploaded
# If so, save the file to a new folder called 'uploads'
# Finally, return a success message

# Run the web server
from flask import Flask, render_template, request, jsonify, session
import os
import pandas as pd
import math
import uuid

from typing import Optional
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'change-me-for-prod')
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
@app.route('/')
def index():
    return render_template('index.html')
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file part"
    file = request.files['file']
    if file.filename == '':
        return "No selected file"
    if file:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        return "File uploaded successfully"


@app.route('/files', methods=['GET'])
def list_files():
    allowed_exts = ('.csv', '.txt', '.xls', '.xlsx')
    files = [f for f in os.listdir(UPLOAD_FOLDER)
             if os.path.isfile(os.path.join(UPLOAD_FOLDER, f)) and f.lower().endswith(allowed_exts)]
    files.sort()
    return jsonify({'files': files}), 200


@app.route('/select_file', methods=['POST'])
def select_file():
    data = request.get_json(silent=True) or {}
    filename = data.get('filename') if isinstance(data, dict) else None
    if not filename:
        # try form data
        filename = request.form.get('filename')
    if not filename:
        return jsonify({'error': 'filename is required'}), 400
    # sanitize and validate
    filename = os.path.basename(filename)
    allowed_exts = ('.csv', '.txt', '.xls', '.xlsx')
    if not filename.lower().endswith(allowed_exts):
        return jsonify({'error': 'Invalid file extension'}), 400
    target = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(target) or not os.path.isfile(target):
        return jsonify({'error': 'File not found'}), 404

    # set session active file
    session['active_file'] = filename
    # ensure session id
    sid = session.get('sid')
    if not sid:
        sid = uuid.uuid4().hex
        session['sid'] = sid

    # clear any existing cache for this session
    cache_dir = 'cache'
    cache_path = os.path.join(cache_dir, f'{sid}.pkl')
    try:
        if os.path.exists(cache_path):
            os.remove(cache_path)
    except Exception:
        pass

    return jsonify({'selected': filename}), 200


@app.route('/session_info', methods=['GET'])
def session_info():
    # Return the currently active filename for this session (if any)
    active = session.get('active_file')
    return jsonify({'active_file': active}), 200
@app.route('/chat', methods=['POST'])
def chat():
    # Accept JSON payload with a 'message' field
    data = request.get_json(silent=True) or {}
    msg = data.get('message') if isinstance(data, dict) else None
    if not msg:
        msg = request.form.get('message', '')
    lower = msg.strip().lower() if isinstance(msg, str) else ''

    # New commands include pagination and full-data browsing
    file_commands = {'show me the average', 'show head', 'show shape', 'describe data', 'show all data'}
    if lower in file_commands or lower.startswith('show page'):
        # find active file from session (if set), otherwise fall back to newest data file
        allowed_exts = ('.csv', '.txt', '.xls', '.xlsx')
        active = session.get('active_file')
        files = [f for f in os.listdir(UPLOAD_FOLDER)
                 if os.path.isfile(os.path.join(UPLOAD_FOLDER, f)) and f.lower().endswith(allowed_exts)]
        if not files:
            return jsonify({'response': 'No uploaded data files found (allowed: .csv, .txt, .xls, .xlsx).'}), 200
        if active and active in files:
            latest = active
        else:
            latest = max(files, key=lambda f: os.path.getmtime(os.path.join(UPLOAD_FOLDER, f)))
        latest_path = os.path.join(UPLOAD_FOLDER, latest)
        # read dataframe
        df = None
        try:
            # Robustly read CSV/Excel. For CSVs, decode bytes with utf-8 (replace errors) to avoid decode failures.
            import io
            if latest_path.lower().endswith(('.csv', '.txt')):
                with open(latest_path, 'rb') as fh:
                    raw = fh.read()
                try:
                    text = raw.decode('utf-8')
                except Exception:
                    text = raw.decode('utf-8', errors='replace')
                df = pd.read_csv(io.StringIO(text))
            else:
                try:
                    df = pd.read_excel(latest_path)
                except Exception:
                    # fallback to reading as CSV if excel read fails
                    with open(latest_path, 'rb') as fh:
                        raw = fh.read()
                    text = raw.decode('utf-8', errors='replace')
                    import io as _io
                    df = pd.read_csv(_io.StringIO(text))
        except Exception as e:
            return jsonify({'response': f'Failed to read the uploaded file: {str(e)}'}), 200

        # produce HTML based on command
        try:
            page_size = 50
            # Helper to cache full dataframe for this session
            cache_dir = 'cache'
            os.makedirs(cache_dir, exist_ok=True)
            sid = session.get('sid')
            if not sid:
                sid = uuid.uuid4().hex
                session['sid'] = sid

            def cache_df(df_to_cache):
                path = os.path.join(cache_dir, f'{sid}.pkl')
                try:
                    pd.to_pickle(df_to_cache, path)
                except Exception:
                    # best-effort
                    pass

            def load_cached_df():
                path = os.path.join(cache_dir, f'{sid}.pkl')
                if os.path.exists(path):
                    try:
                        return pd.read_pickle(path)
                    except Exception:
                        return None
                return None

            def make_page(df_obj, page_num=1, page_size=50):
                total_rows = int(df_obj.shape[0])
                total_pages = max(1, math.ceil(total_rows / page_size))
                page = max(1, min(page_num, total_pages))
                start = (page - 1) * page_size
                end = start + page_size
                sub = df_obj.iloc[start:end]
                html = sub.to_html(classes='data-table', index=False, border=0)
                pagination = {'total_pages': total_pages, 'current_page': page, 'page_size': page_size, 'total_rows': total_rows}
                return html, pagination

            # Pagination command: "show page N"
            if lower.startswith('show page'):
                parts = lower.split()
                try:
                    page_req = int(parts[-1])
                except Exception:
                    return jsonify({'response': 'Invalid page number.'}), 200
                cached = load_cached_df()
                if cached is None:
                    return jsonify({'response': 'No cached dataset found. Run a data command first (e.g. "show all data").'}), 200
                html, pagination = make_page(cached, page_req, page_size)
                return jsonify({'response': html, 'pagination': pagination}), 200

            if lower == 'show head':
                # If dataset is large, cache and return first page
                if df.shape[0] > page_size:
                    cache_df(df)
                    html, pagination = make_page(df, 1, page_size)
                    return jsonify({'response': html, 'pagination': pagination}), 200
                else:
                    html = df.head().to_html(classes='data-table', index=False, border=0)
                    return jsonify({'response': html}), 200
            elif lower == 'show shape':
                import pandas as _pd
                shape_df = _pd.DataFrame({'rows': [df.shape[0]], 'columns': [df.shape[1]]})
                html = shape_df.to_html(classes='data-table', index=False, border=0)
                return jsonify({'response': html}), 200
            elif lower == 'describe data':
                html = df.describe(include='all').to_html(classes='data-table', border=0)
                return jsonify({'response': html}), 200
            elif lower == 'show me the average':
                numeric = df.select_dtypes(include='number')
                if numeric.shape[1] == 0:
                    return jsonify({'response': 'No numeric columns found in the latest uploaded file.'}), 200
                means = numeric.mean().to_dict()
                import pandas as _pd
                mean_df = _pd.DataFrame.from_dict(means, orient='index', columns=['mean'])
                html = mean_df.to_html(classes='data-table', header=True, border=0)
                return jsonify({'response': html, 'averages': {str(k): (float(v) if pd.notna(v) else None) for k, v in means.items()}}), 200
            elif lower == 'show all data':
                # Cache full dataframe and return first page
                cache_df(df)
                html, pagination = make_page(df, 1, page_size)
                return jsonify({'response': html, 'pagination': pagination}), 200
        except Exception as e:
            return jsonify({'response': f'Error processing DataFrame command: {str(e)}'}), 200

    # default: echo
    return jsonify({'response': f'You said: {msg}'}), 200

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
