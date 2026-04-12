# Sky-Trace local development helper script.
# TODO: Replace placeholder commands with robust process orchestration.

Write-Host "[1/3] Start backend"
Write-Host "cd server; python -m venv .venv; .venv\\Scripts\\activate; pip install -r requirements.txt; uvicorn app.main:app --reload"

Write-Host "[2/3] Start frontend"
Write-Host "cd client; npm install; npm run dev"

Write-Host "[3/3] Start desktop"
Write-Host "cd desktop; pip install -r requirements.txt; python main.py"
