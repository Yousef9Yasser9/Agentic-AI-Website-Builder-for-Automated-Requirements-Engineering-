"""
Compatibility entrypoint for the retired Streamlit demo.

The AI Website Builder now runs as:
  - FastAPI backend:  python -m uvicorn backend.app.main:app --reload --port 8000
  - React frontend:   cd frontend && npm run dev

This file intentionally contains no Streamlit imports or UI code.
"""

from __future__ import annotations


def main() -> None:
    print("The Streamlit demo UI has been replaced.")
    print("Start the backend with:")
    print("  python -m uvicorn backend.app.main:app --reload --port 8000")
    print("Start the frontend with:")
    print("  cd frontend")
    print("  npm run dev")


if __name__ == "__main__":
    main()

