# Deploy to Render - Quick Start Script
# This script prepares your local project for deployment

Write-Host "=== The Analyst - Deployment Preparation ===" -ForegroundColor Cyan

# Step 1: Verify Git is installed
Write-Host "`n[1/5] Checking Git installation..." -ForegroundColor Yellow
git --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Git not found. Please install Git first." -ForegroundColor Red
    exit 1
}
Write-Host "✓ Git is installed" -ForegroundColor Green

# Step 2: Verify we're in the right directory
Write-Host "`n[2/5] Checking project directory..." -ForegroundColor Yellow
if (-not (Test-Path "requirements.txt") -or -not (Test-Path "main.py")) {
    Write-Host "ERROR: Not in TheAnalyst project directory!" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Project directory verified" -ForegroundColor Green

# Step 3: Verify deployment files exist
Write-Host "`n[3/5] Verifying deployment files..." -ForegroundColor Yellow
$required_files = @("Procfile", "runtime.txt", "requirements.txt", ".gitignore")
foreach ($file in $required_files) {
    if (Test-Path $file) {
        Write-Host "  ✓ $file" -ForegroundColor Green
    } else {
        Write-Host "  ✗ MISSING: $file" -ForegroundColor Red
    }
}

# Step 4: Show Git status
Write-Host "`n[4/5] Git status:" -ForegroundColor Yellow
git status --short

# Step 5: Instructions
Write-Host "`n[5/5] Ready to deploy! Next steps:" -ForegroundColor Yellow
Write-Host "
1. Ensure all changes are committed:
   git add .
   git commit -m 'Prepare for deployment to Render'

2. Push to GitHub:
   git push origin main

3. Go to https://render.com and sign up

4. Create a new Web Service:
   - Connect your GitHub repository
   - Repository: mohamedshirbeny/TheAnalyst-MVP
   - Build command: pip install -r requirements.txt
   - Start command: gunicorn main:app

5. Add environment variables:
   - FLASK_SECRET_KEY = (random string - generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))')
   - OPENAI_API_KEY = (your OpenAI API key)

6. Click 'Create Web Service' and wait for deployment

Your app will be live at: https://theanalyst-xxxxx.onrender.com

For detailed instructions, see DEPLOYMENT_GUIDE.md
" -ForegroundColor Cyan

Write-Host "=== Deployment Preparation Complete ===" -ForegroundColor Green
