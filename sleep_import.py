"""Map real tracker CSV columns to a local, explicitly timezone-aware timeline."""
import io
from zoneinfo import ZoneInfo
import pandas as pd


def as_utc(value, timezone):
    stamp = pd.Timestamp(value)
    if pd.isna(stamp):
        raise ValueError("A timestamp is missing.")
    if stamp.tzinfo is None:
        stamp = stamp.tz_localize(ZoneInfo(timezone), ambiguous="raise", nonexistent="raise")
    return stamp.tz_convert("UTC")


def normalize_stages(frame, start_column, stage_column, timezone, end_column=None):
    if start_column == stage_column or end_column in {start_column, stage_column}:
        raise ValueError("Choose distinct timestamp and stage columns.")
    starts = [as_utc(v, timezone) for v in frame[start_column]]
    stages = frame[stage_column].astype("string")
    if stages.isna().any() or stages.str.strip().eq("").any():
        raise ValueError("Every row needs a sleep-stage label.")
    data = pd.DataFrame({"start": starts, "stage": stages.str.strip().tolist()}).sort_values("start").reset_index(drop=True)
    if data["start"].duplicated().any():
        raise ValueError("Duplicate start timestamps need to be resolved before import.")
    if end_column:
        # Keep source row alignment when sorting explicit interval ends.
        end_by_start = dict(zip(starts, [as_utc(v, timezone) for v in frame[end_column]]))
        data["end"] = data["start"].map(end_by_start)
    else:
        data["end"] = data["start"].shift(-1)
        data = data.iloc[:-1].copy()  # Last duration is unknown, never invented.
    if data.empty:
        raise ValueError("At least one complete sleep-stage interval is required.")
    duration = (data["end"]-data["start"]).dt.total_seconds()
    if (duration <= 0).any() or (duration > 24*3600).any():
        raise ValueError("Intervals must have positive durations of at most 24 hours.")
    if (data["end"].iloc[:-1].reset_index(drop=True) > data["start"].iloc[1:].reset_index(drop=True)).any():
        raise ValueError("Sleep-stage intervals overlap. Check the source mapping.")
    return data


def render_sleep_import():
    import streamlit as st
    st.header("Sleep-stage timeline")
    st.write("Upload a tracker CSV, choose its actual timestamp and stage columns, and mark when you recorded the dream. Processing stays local.")
    source = st.file_uploader("Sleep tracker CSV", type=["csv"], key="tracker_csv")
    if source is None:
        st.caption("Supports interval start/end columns, or start timestamps where each next row ends the preceding stage.")
        return
    try:
        frame = pd.read_csv(io.BytesIO(source.getvalue()))
        if frame.empty or len(frame.columns)<2:
            raise ValueError("The CSV needs rows and at least two columns.")
    except Exception:
        st.error("Could not read this CSV. Check that it has a header row and valid CSV formatting.")
        return
    st.dataframe(frame.head(5), hide_index=True)
    columns = list(frame.columns)
    start = st.selectbox("Start timestamp column", columns)
    stage = st.selectbox("Sleep-stage column", columns, index=min(1,len(columns)-1))
    end = st.selectbox("End timestamp column", ["Use next row's start", *columns])
    timezone = st.text_input("Timezone for timestamps without an offset (IANA name)", value="America/Chicago")
    rem = st.text_input("Which stage label means REM?", value="REM")
    dream = st.text_input("Dream timestamp (optional, ISO format)", placeholder="2026-11-03T06:30:00-06:00")
    try:
        data = normalize_stages(frame,start,stage,timezone,None if end=="Use next row's start" else end)
        marker = as_utc(dream,timezone) if dream.strip() else None
    except Exception as error:
        st.error(f"Check the mapping, timezone and timestamps: {error}")
        return
    if end=="Use next row's start":
        st.caption("The final source row is omitted because its end time is unknown. Gaps between starts count as the preceding stage; use explicit ends if that is incorrect for your export.")
    rem_rows = data[data["stage"].str.casefold()==rem.strip().casefold()]
    minutes = (rem_rows["end"]-rem_rows["start"]).dt.total_seconds().sum()/60
    st.metric("REM minutes in imported intervals", f"{minutes:.1f}")
    if rem_rows.empty:
        st.info("No stage labels match the REM label you entered.")
    values = [{"start":r.start.isoformat(),"end":r.end.isoformat(),"stage":r.stage} for r in data.itertuples()]
    layers = [{"data":{"values":values},"mark":{"type":"bar","height":22},"encoding":{
        "x":{"field":"start","type":"temporal","title":"Time (UTC)","scale":{"type":"utc"}},
        "x2":{"field":"end"},"y":{"field":"stage","type":"nominal","title":"Stage"},
        "color":{"field":"stage","type":"nominal"},"tooltip":[{"field":"stage"},{"field":"start"},{"field":"end"}]}}]
    if marker is not None:
        layers.append({"data":{"values":[{"dream":marker.isoformat()}]},"mark":{"type":"rule","color":"#ffcc00","strokeWidth":3},
                       "encoding":{"x":{"field":"dream","type":"temporal"},"tooltip":[{"field":"dream","title":"Dream timestamp"}]}})
        if marker<data["start"].min() or marker>data["end"].max():
            st.warning("The dream timestamp falls outside the imported sleep intervals.")
    st.vega_lite_chart({"layer":layers}, use_container_width=True)
    st.caption("Tracker stage labels are estimates. A nearby REM interval does not establish when the dream occurred. Timeline timestamps are shown in UTC.")
    st.download_button("Download normalized stages",data.to_csv(index=False).encode(),file_name="sleep_stages_utc.csv",mime="text/csv")
