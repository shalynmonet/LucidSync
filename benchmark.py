"""Reproducible report-level comparison against the TXMM character annotations.

Only Characters is human coded in these CSVs. Attributes are projected from each
four-symbol code; no human emotion or interaction labels are manufactured.
"""
import ast
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import random
import re
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

from coding_models import DreamCoding
from models import DreamRecord, DreamScene
from meta_client import code_dream, MOCK_MODE, MODEL_ID, CODING_SYSTEM_PROMPT

ROOT = Path(__file__).parent / "data" / "benchmark"
SEED = 42
VERSION = "characters-report-multiset-v1"
CODE = re.compile(r"[1-8](?:[MFIJ][FMXBTADCIYRHWKPOESU][ATCB]|ANI|CZZ)")
CATEGORIES = ("presence", "type", "number_status", "gender", "identity", "age", "full_codes")


def parse_human(value):
    # literal_eval safely reads the legacy [u'1MKA', ...] notation; never eval.
    codes = ast.literal_eval(value)
    if not isinstance(codes, list) or any(not isinstance(c, str) for c in codes):
        raise ValueError("Characters must contain a list of strings.")
    clean = [c.strip().upper() for c in codes if c.strip()]
    if any(not CODE.fullmatch(c) for c in clean):
        raise ValueError("Unrecognized human character code; inspect data before scoring.")
    return clean


def load_reports(root=ROOT):
    reports = []
    for group in ("female", "male"):
        path = root / f"hvdc_norms_{group}.csv"
        with path.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames != ["Report", "Characters"]:
                raise ValueError(f"Unexpected columns in {path.name}: {reader.fieldnames}")
            for row_id, row in enumerate(reader, start=1):
                if not row["Report"].strip():
                    raise ValueError(f"Empty report: {group} row {row_id}")
                reports.append({"id": f"{group}:{row_id}", "group": group,
                                "report": row["Report"], "human_codes": parse_human(row["Characters"])})
    return reports


def sample_reports(reports, size=50, seed=SEED):
    if size < 2 or size % 2:
        raise ValueError("Choose an even sample size of at least two for exact balance.")
    # Independent deterministic group shuffles give nested, balanced samples.
    selected = []
    for group in ("female", "male"):
        pool = [r for r in reports if r["group"] == group]
        if size // 2 > len(pool):
            raise ValueError("Sample exceeds the smaller source file.")
        random.Random(f"{seed}:{group}").shuffle(pool)
        selected.extend(pool[:size // 2])
    random.Random(seed).shuffle(selected)
    return selected


def predicted_codes(coding, report):
    codes, invalid = [], []
    for row in coding.rows:
        if row.category.strip().lower() not in {"character", "characters"}:
            continue
        value = row.code.strip().upper()
        if not CODE.fullmatch(value) or row.source_quote not in report:
            # Reject malformed/non-verbatim predictions visibly instead of hiding them.
            invalid.append({"code": row.code, "reason": "invalid code or non-verbatim evidence"})
        else:
            codes.append(value)
    return codes, invalid


def project(codes):
    # Multisets preserve multiplicities without pretending anonymous codes identify
    # individual entities. Animals/creatures have no human gender/identity/age.
    result = {c: Counter() for c in CATEGORIES}
    result["presence"]["present"] = int(bool(codes))
    for code in codes:
        result["full_codes"][code] += 1
        result["number_status"][code[0]] += 1
        kind = "animal" if code[1:] == "ANI" else "creature" if code[1:] == "CZZ" else "human"
        result["type"][kind] += 1
        if kind == "human":
            for category, index in (("gender", 1), ("identity", 2), ("age", 3)):
                result[category][code[index]] += 1
    return result


def nominal_kappa(human, auto):
    # Each report's sorted attribute multiset is a nominal label. This is NOT
    # character-level aligned kappa: source codes carry no entity/span alignment.
    n = len(human)
    if not n:
        return None
    h, a = Counter(human), Counter(auto)
    observed = sum(x == y for x, y in zip(human, auto)) / n
    expected = sum(h[k] * a[k] for k in h.keys() | a.keys()) / n**2
    return (observed - expected) / (1 - expected) if expected < 1 else None


def compute_metrics(examples):
    evaluated = [r for r in examples if r["status"] == "ok"]
    metrics = []
    for category in CATEGORIES:
        humans, autos, tp, fp, fn, exact = [], [], 0, 0, 0, 0
        for row in evaluated:
            h, a = project(row["human_codes"])[category], project(row["auto_codes"])[category]
            canonical = lambda x: tuple(sorted((k, v) for k, v in x.items() if v))
            humans.append(canonical(h)); autos.append(canonical(a))
            exact += h == a
            tp += sum((h & a).values()); fp += sum((a-h).values()); fn += sum((h-a).values())
        precision = tp/(tp+fp) if tp+fp else None
        recall = tp/(tp+fn) if tp+fn else None
        f1 = 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None
        metrics.append({"category": category, "n": len(evaluated),
                        "agreement_percent": 100*exact/len(evaluated) if evaluated else None,
                        "precision": precision, "recall": recall, "f1": f1,
                        "cohens_kappa": nominal_kappa(humans, autos), "tp": tp, "fp": fp, "fn": fn})
    return metrics


def run_benchmark(size=50, seed=SEED, root=ROOT, progress=None):
    sample = sample_reports(load_reports(root), size, seed)
    cache = root / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    examples = []
    def evaluate(row):
        key = hashlib.sha256(json.dumps({"report": row["report"], "model": MODEL_ID,
            "prompt": CODING_SYSTEM_PROMPT, "version": VERSION, "mock": MOCK_MODE}, sort_keys=True).encode()).hexdigest()
        path = cache / f"{key}.json"
        item = {**row, "status": "ok", "cache_hit": path.exists()}
        try:
            if path.exists():
                coding = DreamCoding.model_validate_json(path.read_text(encoding="utf-8"))
            else:
                # No structuring call is needed: the shared coder consumes raw report text.
                scene = DreamScene(scene_number=1, setting="Not used by benchmark", characters=[], objects=[], actions=[], emotions=[], colors=[], vividness=3)
                record = DreamRecord(dream_report=row["report"], mood_on_waking="not supplied", vividness=3, scenes=[scene])
                coding = code_dream(record)
                path.write_text(coding.model_dump_json(indent=2), encoding="utf-8")
            item["model_response"] = coding.model_dump()
            item["auto_codes"], item["invalid_predictions"] = predicted_codes(coding, row["report"])
            if item["invalid_predictions"]:
                item["status"] = "invalid_prediction"
            item["matched"] = item["status"] == "ok" and Counter(item["human_codes"]) == Counter(item["auto_codes"])
        except Exception as error:
            item.update(status="error", error_type=type(error).__name__, auto_codes=[], matched=False)
        return item
    # Limit concurrency to three requests; collect in sample order for reproducibility.
    with ThreadPoolExecutor(max_workers=3) as executor:
        for index, item in enumerate(executor.map(evaluate, sample)):
            examples.append(item)
            if progress:
                progress(index+1, size)
    metrics = compute_metrics(examples)
    result = {"mode": "MOCK — placeholder outputs, not measured model performance" if MOCK_MODE else "LIVE",
        "mock": MOCK_MODE, "model": MODEL_ID,
        "prompt_sha256": hashlib.sha256(CODING_SYSTEM_PROMPT.encode()).hexdigest(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "seed": seed, "sample_size": size, "sample_ids": [r["id"] for r in sample],
        "evaluated": sum(r["status"] == "ok" for r in examples),
        "failed_or_invalid": sum(r["status"] != "ok" for r in examples),
        "overall_agreement_percent": next(m["agreement_percent"] for m in metrics if m["category"] == "full_codes"),
        "metrics": metrics, "examples": examples, "mapping_version": VERSION,
        "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob("hvdc_norms_*.csv")}}
    (root / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    with (root / "results.csv").open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=["mode", "sample_size", "evaluated", "failed_or_invalid", *metrics[0]])
        writer.writeheader()
        for metric in metrics:
            writer.writerow({"mode": result["mode"], "sample_size": size, "evaluated": result["evaluated"], "failed_or_invalid": result["failed_or_invalid"], **metric})
    return result


def render_benchmark():
    import streamlit as st
    st.header("Human-coder benchmark")
    st.write("TXMM norm reports contain human character codes only. Other Hall–Van de Castle categories are not evaluated.")
    st.caption("Historical reports may contain distressing content and outdated language. Report text and model responses stay in the ignored local data folder.")
    if MOCK_MODE:
        st.warning("MOCK MODE: empty placeholder predictions. These scores are not measured Muse Spark performance.")
    try:
        reports = load_reports()
    except (OSError, ValueError) as error:
        st.error(f"Could not load the benchmark CSV files: {error}")
        return
    size = int(st.number_input("Reports to evaluate (balanced, even number)", min_value=2, max_value=2*min(sum(r['group']==g for r in reports) for g in ('female','male')), value=50, step=2))
    consent = MOCK_MODE or st.checkbox("Send these benchmark reports to Meta for coding (API usage may incur charges).")
    if st.button("Run benchmark", disabled=not consent or size % 2 != 0):
        bar = st.progress(0)
        with st.spinner("Coding reports; completed responses are cached…"):
            result = run_benchmark(size=size, progress=lambda n,total: bar.progress(n/total))
        st.session_state["benchmark_result"] = result
    result = st.session_state.get("benchmark_result")
    if result is None and (ROOT / "results.json").exists():
        result = json.loads((ROOT / "results.json").read_text(encoding="utf-8"))
    if result:
        st.subheader(result["mode"])
        st.write(f"Evaluated {result['evaluated']} / {result['sample_size']}; failed or invalid: {result['failed_or_invalid']}. Seed: {result['seed']}.")
        st.caption("Saved results may use a different sample size or mode from the current settings. Undefined metrics are blank. Failures are excluded and reported above.")
        value = result["overall_agreement_percent"]
        st.metric("Overall exact character-code agreement", f"{value:.1f}%" if value is not None else "N/A")
        st.dataframe(result["metrics"], hide_index=True)
        import pandas as pd
        st.bar_chart(pd.DataFrame(result["metrics"]).set_index("category")[["agreement_percent"]], horizontal=True)
        st.caption("Agreement is exact per-report multiset agreement. Precision/recall/F1 use micro-aggregated multiset overlap; kappa compares nominal report-level multisets, not aligned characters.")
        for matched, title in ((True, "Matched examples"), (False, "Missed examples")):
            st.subheader(title)
            candidates = [r for r in result["examples"] if r["status"] == "ok" and r["matched"] == matched][:3]
            if len(candidates) < 3:
                st.info(f"Only {len(candidates)} qualifying examples available; none are fabricated.")
            for row in candidates:
                with st.expander(row["id"]):
                    st.write(row["report"])
                    left, right = st.columns(2)
                    left.write({"human": row["human_codes"]})
                    right.write({"auto": row["auto_codes"]})
        failures = [r for r in result["examples"] if r["status"] != "ok"]
        if failures:
            with st.expander("Failures and invalid predictions"):
                st.json([{k: v for k,v in r.items() if k in {"id","status","error_type","invalid_predictions"}} for r in failures])
