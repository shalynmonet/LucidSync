"""Local sleep-night logs, reproducible demo data, and descriptive comparisons."""
from datetime import date, time, timedelta
import json
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

ROOT = Path(__file__).parent / "data"


class SleepNight(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    night_date: date
    bedtime: time
    sleep_hours: float = Field(ge=0, le=24)
    position: Literal["back", "side", "stomach", "mixed/unknown"]
    caffeine: float = Field(ge=0, le=30)
    alcohol: float = Field(ge=0, le=30)
    stress: int = Field(ge=1, le=5)
    irregular_schedule: bool
    episode: bool
    episode_time: time | None = None
    duration_minutes: float | None = Field(default=None, ge=0, le=1440)
    experiences: str = ""
    fear: int = Field(default=0, ge=0, le=10)
    synthetic: bool = False

    @model_validator(mode="after")
    def episode_details(self):
        if self.episode and (self.episode_time is None or self.duration_minutes is None):
            raise ValueError("Episode time and duration are required for an episode night.")
        if not self.episode and (self.episode_time is not None or self.duration_minutes is not None or self.experiences or self.fear):
            raise ValueError("Normal nights must not contain episode details.")
        return self


def log_path(demo=False):
    return ROOT / ("sleep_sample_logs.json" if demo else "sleep_logs.json")


def load_nights(demo=False):
    path = log_path(demo)
    if not path.exists():
        return []
    return [SleepNight.model_validate(row) for row in json.loads(path.read_text(encoding="utf-8"))]


def save_nights(nights, demo=False):
    if len({n.night_date for n in nights}) != len(nights):
        raise ValueError("Only one night log per date is allowed.")
    if any(n.synthetic != demo for n in nights):
        raise ValueError("Sample and personal logs must stay separate.")
    path = log_path(demo)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps([n.model_dump(mode="json") for n in nights], indent=2), encoding="utf-8")
    temporary.replace(path)


def sample_nights():
    """Fixed synthetic three-week series; five episodes, four after short nights."""
    nights = []
    for i in range(21):
        episode = i in {2, 5, 9, 14, 19}
        short = i in {2, 5, 8, 9, 14, 17}
        nights.append(SleepNight(
            id=f"sample-night-{i+1}", night_date=date(2026, 10, 1)+timedelta(days=i),
            bedtime=time(1 if short else 23, 30 if short else 0),
            sleep_hours=5.5 if short else 7.5, position="back" if episode else "side",
            caffeine=3 if short else 1, alcohol=1 if i in {4, 11, 18} else 0,
            stress=4 if short else 2, irregular_schedule=short, episode=episode,
            episode_time=time(6, 15) if episode else None,
            duration_minutes=2 if episode else None,
            experiences="I felt unable to move and heard a low humming sound." if episode else "",
            fear=6 if episode else 0, synthetic=True,
        ))
    return nights


def sleep_statistics(nights):
    episodes = [n for n in nights if n.episode]
    normal = [n for n in nights if not n.episode]
    conditions = {
        "under_6_hours": lambda n: n.sleep_hours < 6,
        "back_position": lambda n: n.position == "back",
        "high_stress_4_or_5": lambda n: n.stress >= 4,
        "irregular_schedule": lambda n: n.irregular_schedule,
        "caffeine_recorded": lambda n: n.caffeine > 0,
        "alcohol_recorded": lambda n: n.alcohol > 0,
    }
    def summarize(group):
        return {"nights": len(group),
                "mean_sleep_hours": round(sum(n.sleep_hours for n in group)/len(group), 2) if group else None,
                **{name: sum(predicate(n) for n in group) for name, predicate in conditions.items()}}
    return {"total_nights": len(nights), "episode_nights": summarize(episodes),
            "normal_nights": summarize(normal), "synthetic": bool(nights) and all(n.synthetic for n in nights)}


def render_sleep_tab():
    import streamlit as st
    from meta_client import MOCK_MODE, explain_sleep_patterns, structure_dream, generate_storyboard
    from storage import save_dream_record, save_storyboard

    st.header("Sleep paralysis journal")
    st.info("If episodes are frequent or come with excessive daytime sleepiness, talk to a doctor. This journal does not diagnose or provide treatment.")
    if st.button("Load sample data · 3 weeks"):
        save_nights(sample_nights(), demo=True)
        st.session_state["sleep_demo"] = True
        st.session_state.pop("sleep_explanation", None)
    demo = st.checkbox("View sample logs instead of my personal logs", key="sleep_demo")
    if demo:
        st.warning("SYNTHETIC DEMO DATA — separate from your personal journal.")
    try:
        nights = load_nights(demo)
    except (ValueError, OSError):
        st.error("Could not read the local sleep log. The file has not been overwritten.")
        return

    with st.form("sleep_night_form"):
        st.subheader("Record a night")
        st.caption("Date means the evening the night began. Record normal nights too for a comparison. One log per date.")
        night_date = st.date_input("Night beginning", value=date.today())
        bedtime = st.time_input("Bedtime", value=time(23))
        hours = st.number_input("Sleep hours", min_value=0., max_value=24., value=7., step=.5)
        position = st.selectbox("Sleep position", ["back", "side", "stomach", "mixed/unknown"])
        caffeine = st.number_input("Caffeine servings that day", min_value=0., max_value=30., value=0., step=.5)
        alcohol = st.number_input("Alcohol drinks that day", min_value=0., max_value=30., value=0., step=.5)
        stress = st.slider("Stress", 1, 5, 3)
        irregular = st.checkbox("Irregular sleep schedule")
        episode = st.checkbox("I experienced a sleep-paralysis episode")
        st.caption("The following fields are used only when an episode is recorded.")
        episode_time = st.time_input("Episode time (estimate)", value=time(6))
        duration = st.number_input("Duration estimate (minutes)", min_value=0., max_value=1440., value=1., step=.5)
        experiences = st.text_area("What I saw, heard, or felt")
        fear = st.slider("Fear during the episode", 0, 10, 5)
        save = st.form_submit_button("Save night locally")
    if save:
        try:
            night = SleepNight(night_date=night_date, bedtime=bedtime, sleep_hours=hours,
                position=position, caffeine=caffeine, alcohol=alcohol, stress=stress,
                irregular_schedule=irregular, episode=episode,
                episode_time=episode_time if episode else None,
                duration_minutes=duration if episode else None,
                experiences=experiences.strip() if episode else "", fear=fear if episode else 0,
                synthetic=demo)
            save_nights([*nights, night], demo)
            nights.append(night)
            st.session_state.pop("sleep_explanation", None)
            st.success("Night saved locally.")
        except (ValueError, OSError):
            st.error("Could not save. Check the values and whether that date already has a log.")

    stats = sleep_statistics(nights)
    st.subheader("Logged patterns")
    left, right = st.columns(2)
    left.metric("Episode nights", stats["episode_nights"]["nights"])
    right.metric("Normal nights", stats["normal_nights"]["nights"])
    if nights:
        st.dataframe([n.model_dump(mode="json") for n in sorted(nights, key=lambda n:n.night_date)], hide_index=True)
        table = []
        for condition in ("under_6_hours", "back_position", "high_stress_4_or_5", "irregular_schedule", "caffeine_recorded", "alcohol_recorded"):
            e, n = stats["episode_nights"], stats["normal_nights"]
            table.append({"condition": condition, "episode_nights": f"{e[condition]} / {e['nights']}",
                          "normal_nights": f"{n[condition]} / {n['nights']}"})
        st.dataframe(table, hide_index=True)
        st.caption("Counts describe logged nights only. They do not establish causes, predict episodes, or account for unlogged nights. Caffeine and alcohol counts indicate any use, not timing or dose effects.")
        consent = MOCK_MODE or st.checkbox("Send only these aggregate counts to Meta for a plain-language explanation.")
        if st.button("Explain my logged patterns", disabled=not consent):
            try:
                with st.spinner("Summarizing recorded patterns…"):
                    text = explain_sleep_patterns(stats)
                st.session_state["sleep_explanation"] = {"stats": stats, "text": text}
            except Exception:
                st.error("Could not generate an explanation. Your local numbers and logs are unchanged.")
        explanation = st.session_state.get("sleep_explanation")
        if explanation and explanation["stats"] == stats:
            st.write(explanation["text"])

    st.divider()
    st.subheader("Optional presence illustration")
    st.warning("Content warning: visualizing a frightening presence may be unsettling. This is an illustration of a remembered experience, not evidence that a presence was real.")
    opted_in = st.checkbox("I choose to create a presence illustration")
    if opted_in:
        description = st.text_area("Describe the presence to illustrate", key="presence_description")
        image_consent = MOCK_MODE or st.checkbox("Send this description to Meta to create the illustration.")
        if st.button("Create optional illustration", disabled=not description.strip() or not image_consent):
            try:
                with st.spinner("Creating an illustration…"):
                    record = structure_dream(description, "not supplied", 3)
                    sid, _ = save_dream_record(record)
                    board = generate_storyboard(record, sid, "non-graphic, soft illustrated journal scene")
                    save_storyboard(sid, board)
                st.session_state["presence_board"] = board
            except Exception:
                st.error("Could not create the illustration. Your night logs remain local.")
        board = st.session_state.get("presence_board")
        if board:
            for frame in board.frames:
                if frame.revisions[-1].image_path:
                    st.image(frame.revisions[-1].image_path)
                else:
                    st.info("Mock illustration placeholder; no image was generated.")
