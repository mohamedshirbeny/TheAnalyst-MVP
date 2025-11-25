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
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import pandas as pd
import math
import uuid
from datetime import datetime
from typing import Optional

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'change-me-for-prod')

# Database configuration
instance_path = os.path.join(os.path.dirname(__file__), 'instance')
os.makedirs(instance_path, exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(instance_path, "project.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ============================================================================
# DATABASE MODELS
# ============================================================================

class User(UserMixin, db.Model):
    """User model for authentication"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ai_query_count = db.Column(db.Integer, default=0)  # Track AI queries for Pro tier
    
    # Relationship to files
    files = db.relationship('File', backref='owner', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set the password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches the hash"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


class File(db.Model):
    """File model to track uploaded files and their ownership"""
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<File {self.filename}>'


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    return User.query.get(int(user_id))

# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new user"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        password_confirm = request.form.get('password_confirm', '').strip()
        
        # Validate input
        if not username or not password:
            return render_template('register.html', error='Username and password are required.')
        
        if len(password) < 6:
            return render_template('register.html', error='Password must be at least 6 characters long.')
        
        if password != password_confirm:
            return render_template('register.html', error='Passwords do not match.')
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error='Username already taken.')
        
        # Create new user
        try:
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            return render_template('register.html', error=f'Registration failed: {str(e)}')
    
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login user"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            return render_template('login.html', error='Username and password are required.')
        
        # Find user in database
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            # Login successful
            login_user(user)
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid username or password.')
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return "No file part"
    file = request.files['file']
    if file.filename == '':
        return "No selected file"
    if file:
        # Save file to disk
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        
        # Record file in database linked to current user
        try:
            new_file = File(filename=file.filename, user_id=current_user.id)
            db.session.add(new_file)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return f"File saved but database error: {str(e)}"
        
        return "File uploaded successfully"


@app.route('/api/v1/session', methods=['GET'])
@login_required
def api_session():
    # Combined endpoint: return both files list and active file for current user
    # Only return files owned by the current user
    user_files = File.query.filter_by(user_id=current_user.id).all()
    files = [f.filename for f in user_files]
    files.sort()
    active = session.get('active_file')
    # Validate that active file belongs to current user
    if active:
        if not any(f.filename == active for f in user_files):
            active = None
    return jsonify({'files': files, 'active_file': active, 'username': current_user.username}), 200


@app.route('/select_file', methods=['POST'])
@login_required
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
    
    # CRITICAL SECURITY FIX: Verify file belongs to current user
    user_file = File.query.filter_by(filename=filename, user_id=current_user.id).first()
    if not user_file:
        return jsonify({'error': 'File not found or access denied'}), 404
    
    target = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(target) or not os.path.isfile(target):
        return jsonify({'error': 'File not found on disk'}), 404

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


@app.route('/api/v1/auto_analyze', methods=['POST'])
@login_required
def auto_analyze():
    """Auto-analyze a user's file: head, describe, and histogram of first numeric column"""
    data = request.get_json(silent=True) or {}
    filename = data.get('filename', '').strip()
    
    if not filename:
        return jsonify({'error': 'filename is required'}), 400
    
    # CRITICAL SECURITY FIX: Verify file belongs to current user
    user_file = File.query.filter_by(filename=filename, user_id=current_user.id).first()
    if not user_file:
        return jsonify({'error': 'File not found or access denied'}), 404
    
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found on disk'}), 404
    
    try:
        # Read dataframe
        import io
        if filepath.lower().endswith(('.csv', '.txt')):
            with open(filepath, 'rb') as fh:
                raw = fh.read()
            try:
                text = raw.decode('utf-8')
            except Exception:
                text = raw.decode('utf-8', errors='replace')
            df = pd.read_csv(io.StringIO(text))
        else:
            try:
                df = pd.read_excel(filepath)
            except Exception:
                with open(filepath, 'rb') as fh:
                    raw = fh.read()
                text = raw.decode('utf-8', errors='replace')
                import io as _io
                df = pd.read_csv(_io.StringIO(text))
        
        # Analysis 1: Head
        head_html = df.head().to_html(classes='data-table', index=False, border=0)
        
        # Analysis 2: Describe
        describe_html = df.describe(include='all').to_html(classes='data-table', border=0)
        
        # Analysis 3: Histogram of first numeric column
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        histogram_html = None
        
        if numeric_cols:
            try:
                import plotly.graph_objects as go
                col_name = numeric_cols[0]
                fig = go.Figure(data=[go.Histogram(x=df[col_name], nbinsx=20)])
                fig.update_layout(
                    title=f'Histogram of {col_name}',
                    xaxis_title=col_name,
                    yaxis_title='Frequency',
                    height=400,
                    hovermode='x unified'
                )
                histogram_html = fig.to_html(include_plotlyjs='cdn', div_id='plot_histogram')
            except Exception:
                histogram_html = "<p>Could not generate histogram.</p>"
        
        return jsonify({
            'head': head_html,
            'describe': describe_html,
            'histogram': histogram_html,
            'filename': filename
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Error analyzing file: {str(e)}'}), 500


@app.route('/chat', methods=['POST'])
@login_required
def chat():
    # Accept JSON payload with a 'message' field
    data = request.get_json(silent=True) or {}
    msg = data.get('message') if isinstance(data, dict) else None
    if not msg:
        msg = request.form.get('message', '')
    lower = msg.strip().lower() if isinstance(msg, str) else ''

    # New commands include pagination and full-data browsing
    file_commands = {'show me the average', 'show head', 'show shape', 'describe data', 'show all data'}
    # Commands that start with 'plot' for visualization
    plot_commands = lower.startswith('plot ')
    
    if lower in file_commands or lower.startswith('show page') or plot_commands:
        # CRITICAL SECURITY FIX: Only get files belonging to current user
        user_files = File.query.filter_by(user_id=current_user.id).all()
        files = [f.filename for f in user_files]
        
        if not files:
            return jsonify({'response': 'No uploaded data files found. Please upload a file first.'}), 200
        
        active = session.get('active_file')
        # Verify active file belongs to current user
        if active and not any(f.filename == active for f in user_files):
            active = None
        
        if active:
            latest = active
        else:
            # Get most recently uploaded file for current user
            latest_file = max(user_files, key=lambda f: f.upload_date)
            latest = latest_file.filename
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
            elif lower.startswith('plot '):
                # Extract column name from "plot column_name"
                parts = lower.split()
                if len(parts) < 2:
                    return jsonify({'response': 'Usage: plot column_name'}), 200
                col_name = parts[1]
                if col_name not in df.columns:
                    return jsonify({'response': f'Column "{col_name}" not found in dataset. Available columns: {", ".join(df.columns.tolist())}'}), 200
                # Create histogram using plotly
                try:
                    import plotly.graph_objects as go
                    fig = go.Figure(data=[go.Histogram(x=df[col_name], nbinsx=20)])
                    fig.update_layout(
                        title=f'Histogram of {col_name}',
                        xaxis_title=col_name,
                        yaxis_title='Frequency',
                        height=400,
                        hovermode='x unified'
                    )
                    html_plot = fig.to_html(include_plotlyjs='cdn', div_id='plot_histogram')
                    return jsonify({'response': html_plot}), 200
                except Exception as e:
                    return jsonify({'response': f'Error creating plot: {str(e)}'}), 200
        except Exception as e:
            return jsonify({'response': f'Error processing DataFrame command: {str(e)}'}), 200

    # AI preparation: for unknown commands, prepare data for AI processing
    else:
        try:
            # Prepare basic data summary for AI context
            api_key = os.environ.get('OPENAI_API_KEY')
            if not api_key:
                # No API key configured
                return jsonify({
                    'answer': 'AI feature not configured. Please set OPENAI_API_KEY environment variable.',
                    'model': 'none'
                }), 200
            
            # CRITICAL SECURITY FIX: Load only current user's files for AI context
            user_files = File.query.filter_by(user_id=current_user.id).all()
            
            # Pro tier usage limit check - wrapped for backward compatibility
            try:
                if current_user.ai_query_count >= 10:
                    return jsonify({
                        'error': 'You have reached your monthly limit of 10 AI questions. Upgrade to Pro for unlimited access.'
                    }), 200
            except Exception:
                # Database column doesn't exist on old databases, skip usage limit
                pass
            
            data_context = "No data file loaded."
            if user_files:
                active = session.get('active_file')
                # Verify active file belongs to current user
                if active and not any(f.filename == active for f in user_files):
                    active = None
                
                if active:
                    latest = active
                else:
                    latest_file = max(user_files, key=lambda f: f.upload_date)
                    latest = latest_file.filename
                latest_path = os.path.join(UPLOAD_FOLDER, latest)
                
                # Read dataframe for context
                try:
                    import io
                    if latest_path.lower().endswith(('.csv', '.txt')):
                        with open(latest_path, 'rb') as fh:
                            raw = fh.read()
                        try:
                            text = raw.decode('utf-8')
                        except Exception:
                            text = raw.decode('utf-8', errors='replace')
                        ai_df = pd.read_csv(io.StringIO(text))
                    else:
                        try:
                            ai_df = pd.read_excel(latest_path)
                        except Exception:
                            with open(latest_path, 'rb') as fh:
                                raw = fh.read()
                            text = raw.decode('utf-8', errors='replace')
                            import io as _io
                            ai_df = pd.read_csv(_io.StringIO(text))
                    
                    # Get first 5 rows as context
                    data_context = ai_df.head().to_string()
                except Exception:
                    data_context = "Could not load data file for context."
            
            # Call OpenAI API
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            system_prompt = """You are a data analyst assistant. Answer the user's question based ONLY on the provided data. 
Be concise and direct in your analysis. If the data doesn't contain information to answer the question, say so clearly."""
            
            user_prompt = f"""Here is the first 5 rows of the uploaded data:

{data_context}

User question: {msg}

Please answer this question based on the data provided."""
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            ai_answer = response.choices[0].message.content
            
            # Increment AI query count and save - wrapped for backward compatibility
            try:
                current_user.ai_query_count += 1
                db.session.commit()
            except Exception:
                # Database column doesn't exist on old databases, skip counter increment
                pass
            
            return jsonify({
                'answer': ai_answer,
                'model': 'gpt-4o',
                'message': msg,
                'data_loaded': data_context != "No data file loaded."
            }), 200
            
        except Exception as e:
            return jsonify({
                'answer': f'Error calling AI model: {str(e)}',
                'model': 'openai',
                'error': True
            }), 200

if __name__ == '__main__':
    # Initialize the database
    with app.app_context():
        db.create_all()
        print("Database initialized successfully.")
    
    app.run(debug=True, use_reloader=False)
