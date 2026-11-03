# LucidSync

LucidSync is a research and wellness tool that turns a morning dream memory into
structured, visualized, and labeled data. It is not a medical device and does
not diagnose.

## Current workflow: capture, code, storyboard, refine

The Streamlit form captures a report, waking mood, and vividness rating. Pydantic
models validate ordered scenes, stable character identities, objects, actions,
emotions, colors, and scene vividness. Each submitted record is saved under its
own `data/` session folder, which Git ignores.

The coding view asks Muse Spark for evidence-backed Hall/Van de Castle labels,
including the character, social interaction, activity, outcome, fortune,
emotion, setting, object, and descriptive-element categories. Each row includes
a short dream-report quote. In mock mode no content labels are invented.

Muse Image creates one local storyboard image per scene. Correction rounds are
chained to the prior image response, logged beside the image, and can be locked
with “That’s it”. Character descriptions are repeated in each scene prompt to
help preserve appearance. Live requests use the same Meta key and need the
consent checkbox in the app.

### Windows setup (PowerShell)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
streamlit run app.py
```

Keep `MOCK_MODE=true` to exercise the app without sending dream text to Meta.
For live structuring, coding, or image generation, set your key in `.env` as
`META_API_KEY=...` and set `MOCK_MODE=false`. The app asks for consent before
sending dream details. Image generation and refinement can incur API usage
charges. Never commit `.env`; local dream records and generated images under
`data/` are ignored as well.

## Project layout

```text
.
├── app.py             # Streamlit UI entry point
├── models.py          # Pydantic dream and scene schemas
├── coding_models.py   # Evidence-backed Hall/Van de Castle coding schema
├── storyboard_models.py # Image and revision history schemas
├── meta_client.py     # Central adapter for Meta API calls
├── storage.py         # Local-only dream record persistence
├── requirements.txt   # Python dependencies
├── .env.example       # Safe configuration template
└── data/              # Created at runtime; private and git-ignored
```

## Meta models

Dream structuring uses Muse Spark through Meta Model API's OpenAI-compatible
Chat Completions interface with Pydantic structured output. All API traffic is
contained in `meta_client.py`. Storyboard generation and corrections use Muse
Image through the Responses API (`muse-image-1.0`).

## Privacy

Dream data is intended to stay local. Do not add session data, API credentials,
or private benchmark reports to a public repository.
