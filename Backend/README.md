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
   python -m venv venv
   .\venv\bin\Activate.ps1
   ```

3. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

## Running the Server

Run the development server with hot-reload:
```powershell
uvicorn main:app --reload
```

## API Documentation
Once running, open your browser to:
- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
