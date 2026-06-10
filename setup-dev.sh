#!/bin/bash
set -e

echo "=== ParallaxLane Local Development Setup ==="

# Backend setup
echo ""
echo "--- Setting up Backend ---"
cd backend

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "[!] Created .env from .env.example — EDIT IT BEFORE RUNNING"
else
  echo "[ok] .env already exists"
fi

python3 -m venv venv
source venv/bin/activate

echo "[*] Installing Python dependencies..."
pip install -r requirements.txt --quiet

echo "[*] Running migrations..."
python manage.py migrate

echo "[*] Creating superuser (optional — press Ctrl+C to skip)"
python manage.py createsuperuser || true

echo "[ok] Backend ready. Run with:"
echo "    source venv/bin/activate && python manage.py runserver"

# Frontend setup
echo ""
echo "--- Setting up Frontend ---"
cd ../frontend

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "[!] Created frontend .env from .env.example"
fi

echo "[*] Installing Node dependencies..."
npm install

echo "[ok] Frontend ready. Run with:"
echo "    npm run dev"

echo ""
echo "=== Setup Complete ==="
echo "Start backend: cd backend && source venv/bin/activate && python manage.py runserver"
echo "Start frontend: cd frontend && npm run dev"
