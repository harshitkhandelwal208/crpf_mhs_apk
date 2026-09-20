web: (cd backend 2>/dev/null || true) && python manage.py migrate && python -m uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1 --proxy-headers --forwarded-allow-ips=*
