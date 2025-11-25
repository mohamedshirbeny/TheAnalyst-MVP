# The Analyst - Deployment Guide to Render

## Overview
This guide walks you through deploying "The Analyst" Flask application to Render, a modern cloud platform. The app will be live on the internet with a public URL.

---

## Prerequisites
- GitHub account with the repository pushed (already done: `mohamedshirbeny/TheAnalyst-MVP`)
- Render account (free tier available)
- OpenAI API key
- A Render PostgreSQL database (or use SQLite - but PostgreSQL recommended for production)

---

## Step 1: Prepare Your Local Repository
**Status: COMPLETE**

The following files have been added to support deployment:

✅ `Procfile` - Tells Render how to run the app using Gunicorn
✅ `runtime.txt` - Specifies Python version (3.11.9)
✅ `requirements.txt` - Updated with gunicorn==21.2.0

### What each file does:
- **Procfile**: Contains command `web: gunicorn main:app`
  - Instructs Render to use Gunicorn as the web server
  - Points to Flask app instance in `main.py`

- **runtime.txt**: Specifies exact Python version
  - Ensures consistency between local and production environments

- **requirements.txt**: Lists all dependencies
  - Gunicorn handles serving requests (replaces Flask development server)
  - All other packages (Flask, pandas, openai, etc.) already listed

---

## Step 2: Push Latest Changes to GitHub

```bash
cd C:\Users\Mohamed-elsherbeeny\Desktop\TheAnalyst

# Stage all files
git add Procfile runtime.txt requirements.txt

# Commit
git commit -m "Add deployment configuration: Procfile, runtime.txt, and gunicorn"

# Push to main branch
git push origin main
```

Verify at: https://github.com/mohamedshirbeny/TheAnalyst-MVP

---

## Step 3: Create a Render Account & Connect GitHub

### 3a. Sign Up for Render
1. Go to https://render.com
2. Click **"Sign Up"** (top right)
3. Choose **"Sign up with GitHub"**
4. Authorize Render to access your GitHub account
5. Complete account creation

### 3b. Create a New Web Service
1. From Render Dashboard, click **"New +"** (top right)
2. Select **"Web Service"**
3. Under "Connect a repository":
   - Click **"Connect account"** (if not already connected)
   - Select **`mohamedshirbeny/TheAnalyst-MVP`**
   - Click **"Connect"**

### 3c. Configure the Web Service

**Name:**
```
theanalyst
```

**Environment:** 
```
Python 3
```

**Build Command:**
```
pip install -r requirements.txt
```

**Start Command:**
```
gunicorn main:app
```

**Region:** Choose closest to you (e.g., "US East (N. Virginia)")

**Instance Type:** 
- Select **"Free"** for testing, or **"Starter"** for better performance

### 3d. Add Environment Variables
Before deploying, add your secrets:

1. Scroll down to **"Environment"** section
2. Click **"Add Environment Variable"**
3. Add the following variables:

| Key | Value | Description |
|-----|-------|-------------|
| `FLASK_SECRET_KEY` | `your-secret-key-here-change-this` | Change to a random string for production |
| `OPENAI_API_KEY` | `sk-proj-xxxxx...` | Your actual OpenAI API key |

**Example FLASK_SECRET_KEY** (generate a random one):
```
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

4. Click **"Create Web Service"** to deploy!

---

## Step 4: Monitor Deployment

### During Deployment:
1. Render will automatically:
   - Clone your GitHub repo
   - Install dependencies from `requirements.txt`
   - Run `gunicorn main:app` using the Procfile

2. Watch the **"Logs"** tab for real-time output
   - Look for: `Database initialized successfully.`
   - Then: `Listening on http://0.0.0.0:PORT`

### Common Issues & Solutions:

**Issue: "ModuleNotFoundError: No module named 'flask'"**
- Solution: Ensure all dependencies are in `requirements.txt`
- Current setup: All packages listed ✅

**Issue: "Address already in use"**
- Solution: Gunicorn will use PORT from environment variable (automatic)
- Render handles port binding automatically ✅

**Issue: "Database file not found"**
- Solution: App auto-creates SQLite database on startup
- File stored in `instance/project.db` ✅

---

## Step 5: Access Your Live Application

After deployment completes:

1. Go to Render Dashboard
2. Click on **"theanalyst"** web service
3. Copy the **URL** (looks like: `https://theanalyst-xxxxx.onrender.com`)
4. Open in browser and test!

### Test the Application:
1. Click **"Register"** → Create a new account
2. Login with your credentials
3. Upload a CSV file
4. Try commands: `show head`, `show shape`, `plot column_name`
5. Ask a question to test AI integration

---

## Step 6: Production Database Setup (Optional but Recommended)

SQLite works for small deployments, but for production:

### Option A: Use PostgreSQL on Render (Recommended)

1. In Render Dashboard, click **"New +"** → **"PostgreSQL"**
2. Create a free PostgreSQL instance
3. Get the **Database URL**
4. Update main.py database config:

```python
# main.py (around line 30)
db_url = os.environ.get('DATABASE_URL')
if db_url and db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url or f'sqlite:///{os.path.join(instance_path, "project.db")}'
```

5. Add `DATABASE_URL` environment variable in Web Service settings
6. Redeploy

### Option B: Keep SQLite (Current Setup)
- Works fine for MVP/testing
- Files stored in `instance/project.db`
- Note: Files uploaded are stored in `uploads/` directory (ephemeral on free tier)

---

## Step 7: Set Up Custom Domain (Optional)

1. In Render Web Service settings, scroll to **"Custom Domains"**
2. Enter your domain (e.g., `analyst.yourdomain.com`)
3. Update DNS records as instructed
4. Render auto-provisions SSL certificate

---

## Step 8: Environment Variables Reference

### Required Variables:
- **OPENAI_API_KEY**: Your OpenAI API key (for AI features)
- **FLASK_SECRET_KEY**: Secret key for session encryption

### Auto-Provided by Render:
- **PORT**: Automatically set (no need to configure)
- **DATABASE_URL**: If using PostgreSQL

### Example .env file (for local testing):
```
FLASK_SECRET_KEY=your-secret-key-here
OPENAI_API_KEY=sk-proj-xxxxx...
```

---

## Step 9: Monitoring & Logs

### View Live Logs:
1. Render Dashboard → Select "theanalyst"
2. Click **"Logs"** tab
3. Real-time application logs appear here

### Common Log Messages:
```
Database initialized successfully.
Listening on http://0.0.0.0:10000
```

### Track Errors:
- Any application errors appear in logs
- Database connection issues show here
- API errors logged for debugging

---

## Step 10: Continuous Deployment

Render automatically redeploys when you push to GitHub:

1. Make changes locally
2. Commit: `git commit -m "Your message"`
3. Push: `git push origin main`
4. Render automatically:
   - Pulls latest code
   - Installs dependencies
   - Restarts the service

---

## Troubleshooting

### App won't start - "Python version mismatch"
**Solution:** Check `runtime.txt` has a valid Python version
```
python-3.11.9
```

### Uploads not persisting - "File not found after upload"
**Problem:** Free tier uses ephemeral storage (resets on redeploy)
**Solution:** 
- Use PostgreSQL + store file metadata in database
- Or upgrade to Starter tier for persistent storage

### Database connection errors
**Check:** 
- Environment variables set correctly
- DATABASE_URL format is valid
- PostgreSQL instance is running (if using PostgreSQL)

### "403 Forbidden" errors
**Check:**
- FLASK_SECRET_KEY is set
- Session cookie settings
- User is logged in

---

## Rollback & Redeployment

### If something breaks after deploy:

1. **Revert code** on GitHub:
   ```bash
   git revert HEAD
   git push origin main
   ```

2. **Render auto-redeploys** from new commit

3. **Or manually redeploy**:
   - Render Dashboard → theanalyst → **"Manual Deploy"** → **"Deploy latest commit"**

---

## Performance Tips

1. **Use Render Starter tier or higher** for consistent performance
2. **Enable PostgreSQL** if storing large datasets
3. **Add caching** for frequently analyzed files
4. **Monitor logs** for slow queries or errors

---

## Security Checklist

✅ FLASK_SECRET_KEY set to random value (not default)
✅ OPENAI_API_KEY kept as environment variable (not in code)
✅ Database has encrypted admin passwords
✅ SQLAlchemy configured with SQL injection protection
✅ User files isolated per user (multi-tenant support)
✅ Werkzeug password hashing with strong salt

---

## Summary

| Step | Task | Status |
|------|------|--------|
| 1 | Prepare local repo | ✅ Complete |
| 2 | Push to GitHub | 👉 **Do this next** |
| 3 | Create Render account & connect GitHub | 👉 **Then this** |
| 4 | Configure Web Service | 👉 **Then this** |
| 5 | Add environment variables | 👉 **Then this** |
| 6 | Deploy & test | 👉 **Finally this** |

**Estimated time to live:** 10-15 minutes

---

## Support Resources

- Render Docs: https://render.com/docs
- Flask Deployment: https://flask.palletsprojects.com/en/3.0.x/deploying/
- Gunicorn Docs: https://gunicorn.org/
- OpenAI API: https://platform.openai.com/docs/api-reference

---

## Next Steps After Deployment

1. ✅ Share the live URL: `https://theanalyst-xxxxx.onrender.com`
2. ✅ Test all features with real users
3. ✅ Monitor logs and performance
4. ✅ Consider custom domain
5. ✅ Scale if needed (upgrade to higher tier)

**Your application is now live on the internet! 🚀**
