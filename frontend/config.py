import os


API_URL = (
    os.getenv("BOOKLOOP_API_URL")
    or os.getenv("API_URL")
    or "https://bookloop-api-kade.onrender.com"
).rstrip("/")