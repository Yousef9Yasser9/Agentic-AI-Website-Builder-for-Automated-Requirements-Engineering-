"""
Quick server diagnostic script
Run this to see why the server won't start
"""
import subprocess
import sys
from pathlib import Path

# Find the most recent generated project
projects_dir = Path("generated_apps/projects")
projects = [p for p in projects_dir.iterdir() if p.is_dir() and (p / "v1").exists()]

if not projects:
    print("❌ No generated projects found")
    sys.exit(1)

# Use the most recent one
recent = max(projects, key=lambda p: p.stat().st_mtime)
project_dir = recent / "v1"

print(f"📁 Testing project: {project_dir}")
print(f"{'='*60}\n")

# Check structure
print("Checking structure...")
files_to_check = [
    "app/main.py",
    "app/models.py",
    "app/auth.py",
    "app/db.py",
    ".venv/Scripts/python.exe",
    ".venv/Scripts/uvicorn.exe",
]

for file in files_to_check:
    path = project_dir / file
    exists = "✅" if path.exists() else "❌"
    print(f"{exists} {file}")

print(f"\n{'='*60}\n")

# Try to import the app
python_exe = project_dir / ".venv" / "Scripts" / "python.exe"
if not python_exe.exists():
    print("❌ Python venv not found")
    sys.exit(1)

print("Testing Python imports...")
result = subprocess.run(
    [str(python_exe), "-c", "from app.main import app; print('✅ App imports successfully')"],
    cwd=str(project_dir),
    capture_output=True,
    text=True
)

print(result.stdout)
if result.stderr:
    print("❌ ERRORS:")
    print(result.stderr)

print(f"\n{'='*60}\n")

# Try to start server (will fail, but we'll see the error)
print("Attempting to start server...")
uvicorn_exe = project_dir / ".venv" / "Scripts" / "uvicorn.exe"
proc = subprocess.Popen(
    [str(uvicorn_exe), "app.main:app", "--port", "8100"],
    cwd=str(project_dir),
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

import time
time.sleep(5)  # Wait 5 seconds

if proc.poll() is None:
    print("✅ Server started successfully!")
    proc.terminate()
else:
    print(f"❌ Server exited with code {proc.returncode}")
    stdout, stderr = proc.communicate()
    if stdout:
        print("\nSTDOUT:")
        print(stdout)
    if stderr:
        print("\nSTDERR:")
        print(stderr)
