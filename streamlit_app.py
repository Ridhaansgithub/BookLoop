import os

# Ensure frontend reads API_URL from environment; default to localhost for local testing.
os.environ.setdefault('API_URL', os.getenv('API_URL', 'http://127.0.0.1:8000'))

# Import the Streamlit app module which runs at import time
import frontend.App
