# Foundry Backend

## Prerequisites
- Python 3.8+
- Environment variable `GEMINI_API_KEY` set in `../.env`

## Setup

1. **Navigate to the backend directory:**
   ```powershell
   cd c:\Users\Indrajeet\OneDrive\Documents\Foundry\Backend
   ```

2. **Create a virtual environment (optional but recommended):**
   ```powershell
   C:\Users\Indrajeet\AppData\Local\Programs\Python\Python313\python.exe -m venv venv

   .\venv\Scripts\Activate.ps1
   ```

Install rust and vs build tools
3. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

   cd c:\Users\Indrajeet\OneDrive\Documents\Foundry\Backend
C:\Users\Indrajeet\AppData\Local\Programs\Python\Python313\python.exe -m venv venv

   .\venv\Scripts\Activate.ps1
   uvicorn main:app --reload

## Running the Server

Run the development server with hot-reload:
```powershell
uvicorn main:app --reload
```

## API Documentation
Once running, open your browser to:
- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

To read tables
# Navigate to backend if not already there
cd Backend
# List all tables in the database
sqlite3 foundry_v2.db ".tables"

sqlite3 foundry_v2.db "SELECT * FROM users;"