import os
from dotenv import load_dotenv

# Load environment variables from parent directory
# This assumes config.py is in Foundry/Backend/
base_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(base_dir, '..', '.env')
load_dotenv(env_path)

class Settings:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    @staticmethod
    def validate():
        if not Settings.GEMINI_API_KEY:
            print("WARNING: GEMINI_API_KEY not found in .env file at", env_path)
        else:
            print("Configuration loaded. GEMINI_API_KEY is set.")

settings = Settings()
