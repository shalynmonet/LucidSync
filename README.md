# LucidSync

LucidSync is a research and wellness tool that turns a morning dream memory into
structured, visualized, and labeled data. It is not a medical device and does
not diagnose.

## Milestone 1: scaffold

This milestone includes the Streamlit entry point, dependency list, environment
template, and private-data defaults. Meta API calls are intentionally not
implemented until the API documentation is available.

### Windows setup (PowerShell)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
streamlit run app.py
```

Keep `MOCK_MODE=true` while working without live model calls. When you're ready
to use the Meta Model API, put your key in `.env` as `META_API_KEY=...` and set
`MOCK_MODE=false`. Never commit `.env`; local dream records under `data/` are
ignored as well.

## Project layout

```text
.
├── app.py             # Streamlit UI entry point
├── meta_client.py     # Central adapter for future Meta API calls
├── requirements.txt   # Python dependencies
├── .env.example       # Safe configuration template
└── data/              # Created at runtime; private and git-ignored
```

## Meta models

No model endpoints or request formats have been assumed. Once the API docs are
available, all Meta Model API traffic will go through `meta_client.py`.

## Privacy

Dream data is intended to stay local. Do not add session data, API credentials,
or private benchmark reports to a public repository.
