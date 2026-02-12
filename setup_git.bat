@echo off
echo Initializing Git repository...
git init
if %errorlevel% neq 0 (
    echo Error: Failed to initialize git repository.
    pause
    exit /b %errorlevel%
)

echo Adding files...
git add .
if %errorlevel% neq 0 (
    echo Error: Failed to add files.
    pause
    exit /b %errorlevel%
)

echo Committing files...
git commit -m "Initial commit of AI Cost Profiler"
if %errorlevel% neq 0 (
    echo Error: Failed to commit files.
    pause
    exit /b %errorlevel%
)

echo Renaming branch to main...
git branch -M main
if %errorlevel% neq 0 (
    echo Error: Failed to rename branch.
    pause
    exit /b %errorlevel%
)

echo Adding remote origin...
git remote add origin https://github.com/koopatroopa787/AI-cost-Profiler.git
if %errorlevel% neq 0 (
    echo Error: Failed to add remote origin. Check if it already exists or URL is wrong.
    echo Trying to set-url in case it exists...
    git remote set-url origin https://github.com/koopatroopa787/AI-cost-Profiler.git
)

echo.
echo ========================================================
echo Repository initialized and committed.
echo To push code to GitHub, please run:
echo.
echo git push -u origin main
echo.
echo (You may need to sign in to GitHub)
echo ========================================================
pause
