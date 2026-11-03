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

Corrections now ask Muse Spark to update the structured scene before Muse Image
renders the revision. The original report is retained. Each revision stores its
instruction, render prompt, round number, and structured record snapshot.
Coding is cleared after a correction so it can be regenerated deliberately.

## Grounded labeling and dataset export

After every frame is locked, **Label locked scenes** sends each character and
object name separately to SAM 3.1. The official Meta parser decodes the masks;
OpenCV/NumPy place them on the source image and draw labeled overlays. Missing
matches and multiple matches are shown for review. A name can match several
instances, so those candidates require human review before research use.

**Download session dataset (.zip)** exports final images, PNG masks, overlays,
the DreamRecord, saved coding JSON/CSV when available, storyboard correction
history, and COCO-style annotations with entity IDs and uncompressed RLE masks.
Mock mode exports no invented masks. Unlocking a frame invalidates its dataset.
All exports remain local until you choose to share them.

SAM integration follows the [Meta segmentation guide](https://dev.meta.ai/docs/sam/segmenting)
and uses `sam-3.1` through the same central API adapter.

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

## Human-coder benchmark (milestone 7)

The **Benchmark** tab loads `data/benchmark/hvdc_norms_female.csv` (490 reports)
and `hvdc_norms_male.csv` (491 reports) from
[dljve/TXMM](https://github.com/dljve/TXMM). Both files have exactly `Report` and
`Characters` columns. These data support character evaluation only: emotions,
aggression, friendliness and all other non-character categories are **not scored**.
Historical reports can contain distressing content and outdated language.

The default sample is 50 reports, 25 from each file, using seed 42. Choose another
even sample size in the UI. Source-file group labels are retained as supplied;
they describe the files, not an inferred gender of anyone in a report. Independent
seeded shuffles make larger samples include the smaller sample. Saved results
record sample IDs, source SHA-256 hashes, model, prompt-sensitive cache and mode.

Character cells are legacy Python-list strings such as `[u'1MKA', u'1ANI']`.
They are read using `ast.literal_eval`, never `eval`. Empty-string placeholders
(15 female-file entries, 30 male-file entries) are dropped. Repeated nonempty codes
are preserved: distinct characters can share the same code. Unsupported codes
cause a visible validation error rather than being guessed.

Mapping rules (also documented in `benchmark.py`):

- Human and model codes use number/status + gender + identity + age, e.g.
  `1MKA` = individual, male, known, adult. Animals use `ANI`; unknown creatures
  use `CZZ` instead of human attributes. The dreamer is excluded.
- The main app and benchmark use the same `code_dream` function and prompt.
  Character rows must contain one exact code and a verbatim report quote.
  Malformed codes or unsupported evidence mark the response invalid and are
  reported separately; API failures and invalid responses are excluded from
  scored denominators, so always read coverage beside the scores.
- Each report is projected into multisets for full codes, type, number/status,
  gender, identity and age, plus binary character presence. Animals/creatures
  contribute no human gender, identity or age values. No entity alignment is
  claimed because source character lists have no entity IDs or report spans.
- Percent agreement is the fraction of reports with exactly equal multisets for
  that attribute. Overall agreement is exact full-code-multiset agreement, not
  an average that double-counts correlated character attributes.
- Precision, recall and F1 use micro-aggregated multiset overlap (minimum count
  per label). Presence uses positive-class binary metrics. Undefined denominators
  are blank, not perfect scores.
- Cohen's kappa treats each report's complete attribute multiset as a nominal
  label. It is report-level kappa, **not aligned character-level kappa**. It is
  blank if chance agreement is one or there are no valid reports. This protocol
  differs from the TXMM paper's matching procedure and scores are not directly
  comparable with its published percent-perfect-agreement results.

Every validated model response is cached in `data/benchmark/cache`, keyed by
report, model, full coding prompt, mapping version and mock/live mode. Prompt
changes invalidate the cache; sample size changes reuse applicable responses.
Reruns retry errors but reuse cached invalid predictions so they remain auditable.
The tab displays up to three exact matches and three misses with both code lists;
when fewer exist it says so. Results go to `results.json` and `results.csv`.
All benchmark data, caches, and report text remain excluded from GitHub.

With `MOCK_MODE=true`, predictions are empty placeholders. Mock results and cache
entries are clearly marked and isolated from live results; they are not evidence
of model performance. Live runs require explicit consent in the tab and incur
normal API usage. The UI shows the saved run's mode/sample size to distinguish it
from current settings.

### Measured live run — November 3, 2026

Muse Spark `muse-spark-1.3`, seed 42, 50 reports (25 per source file): all 50
responses were valid; none were excluded for failures or invalid predictions.
These are descriptive results on this historical norm sample, not a clinical
validation or evidence of generalization to new dreamers.

| Character comparison | Exact report agreement | Micro F1 | Report-level kappa |
| --- | ---: | ---: | ---: |
| Presence | 98% | 0.990 | 0.658 |
| Type | 72% | 0.939 | 0.665 |
| Number/status | 64% | 0.893 | 0.603 |
| Gender | 46% | 0.772 | 0.440 |
| Identity | 46% | 0.748 | 0.447 |
| Age | 66% | 0.911 | 0.590 |
| Full codes (overall) | 30% | 0.595 | 0.295 |

Overall full-code precision was 0.591 and recall 0.600. Strict full-code agreement
requires every character code and its multiplicity to match within a report.
Character presence performs much better than complete attribute coding; show
both in the demo rather than describing the tool as a replacement for human
coders. Full results and examples are saved locally in `data/benchmark/results.json`
and `results.csv`; no reports or cached predictions are published here.
