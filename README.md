# Expense Sharing Service

FastAPI backend and Streamlit UI for managing shared expenses, settlements, balances, and Gemini-generated group summaries.

## Requirements

- Python 3.10 or newer
- A Gemini API key for AI summaries

## Setup

```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add your Gemini API key to `.env`:

```dotenv
GEMINI_API_KEY="your_real_gemini_api_key"
API_BASE_URL="http://localhost:8000"
```

The `.env` file is ignored by Git. Do not commit real API keys.

## Run the backend

In one terminal, from the project root:

```bash
source .venv/bin/activate
set -a
source .env
set +a
uvicorn app.main:app --reload
```

The API is available at <http://localhost:8000>; interactive API documentation is at <http://localhost:8000/docs>.

## Run the Streamlit UI

In a second terminal, from the project root:

```bash
source .venv/bin/activate
export API_BASE_URL="http://localhost:8000"
streamlit run streamlit_app.py
```

The Streamlit UI defaults to `http://localhost:8000` for the backend. Set `API_BASE_URL` in this terminal if your backend uses a different address. Do not source `.env` in the Streamlit terminal: it contains the Gemini key, which belongs only in the FastAPI environment and is never sent by Streamlit.
