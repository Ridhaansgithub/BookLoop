import os

# Ensure frontend reads API_URL from environment; default to localhost for local testing.
os.environ.setdefault("BOOKLOOP_API_URL", os.getenv("BOOKLOOP_API_URL") or os.getenv("API_URL") or "http://127.0.0.1:8000")
os.environ.setdefault("API_URL", os.environ["BOOKLOOP_API_URL"])

from frontend.App import main


if __name__ == "__main__":
    main()
