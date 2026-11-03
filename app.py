"""LucidSync dream capture, content coding, and visual storyboard workflow."""

from pathlib import Path

import streamlit as st

from meta_client import (
    MOCK_MODE,
    code_dream,
    generate_storyboard,
    refine_storyboard_frame,
    structure_dream,
)
from storage import (
    load_storyboard,
    save_dream_coding,
    save_dream_record,
    save_storyboard,
)


st.set_page_config(page_title="LucidSync", page_icon="🌙", layout="centered")

st.title("LucidSync")
st.write(
    "Turn a morning dream memory into structured, visualized, and labeled data."
)
st.info(
    "Research and wellness tool, not a medical device. LucidSync does not diagnose."
)

if MOCK_MODE:
    st.info("Mock mode is on. Dream text stays local and placeholder scene data is used.")
else:
    st.warning(
        "When you submit, your dream report and waking mood will be sent to the "
        "Meta Model API to create the structured record."
    )
    live_consent = st.checkbox(
        "I understand my dream report and scene descriptions will be sent to Meta Model API when I structure, code, or generate/refine images."
    )

with st.form("dream_capture_form"):
    st.subheader("Capture a dream")
    dream_report = st.text_area(
        "Dream report",
        placeholder="Write what you remember, in your own words.",
        height=180,
    )
    mood_on_waking = st.text_input(
        "Mood on waking",
        placeholder="For example: curious, unsettled, peaceful",
    )
    vividness = st.slider("Overall vividness", min_value=1, max_value=5, value=3)
    submitted = st.form_submit_button("Structure dream")

if submitted:
    if not dream_report.strip():
        st.error("Add a dream report before submitting.")
    elif not mood_on_waking.strip():
        st.error("Add the mood you woke with before submitting.")
    elif not MOCK_MODE and not live_consent:
        st.warning("Check the consent box before sending the report to Meta Model API.")
    else:
        try:
            with st.spinner("Structuring the dream report…"):
                record = structure_dream(
                    dream_report=dream_report,
                    mood_on_waking=mood_on_waking,
                    vividness=vividness,
                )
                session_id, record_path = save_dream_record(record)
            st.session_state["dream_record"] = record
            st.session_state["dream_session_id"] = session_id
            st.session_state["dream_record_path"] = str(record_path)
            st.session_state.pop("dream_coding", None)
            st.session_state.pop("storyboard", None)
        except RuntimeError as error:
            # These messages are authored locally and do not include the dream text.
            st.error(f"Could not structure this dream. {error}")
        except Exception:
            # Avoid showing provider errors that might echo private request details.
            st.error(
                "Could not structure this dream. Check the API setup or try again. "
                "Your report remains saved only in this app unless live mode was enabled."
            )

record = st.session_state.get("dream_record")
if record is not None:
    st.success(
        f"Saved dream session {st.session_state['dream_session_id']} locally."
    )
    st.caption(f"Record file: {st.session_state['dream_record_path']}")
    st.subheader("Structured scenes")

    for scene in record.scenes:
        with st.expander(f"Scene {scene.scene_number}: {scene.setting}", expanded=True):
            st.write(f"**Vividness:** {scene.vividness} / 5")
            st.write("**Characters**")
            if scene.characters:
                for character in scene.characters:
                    st.write(
                        f"- {character.name} (`{character.id}`): "
                        f"{character.visual_description}"
                    )
            else:
                st.write("- None identified")

            st.write("**Objects**")
            if scene.objects:
                for dream_object in scene.objects:
                    st.write(
                        f"- {dream_object.name} (`{dream_object.id}`): "
                        f"{dream_object.visual_description}"
                    )
            else:
                st.write("- None identified")

            st.write("**Actions**")
            st.write("- " + ("\n- ".join(scene.actions) if scene.actions else "None identified"))
            st.write("**Emotions:** " + (", ".join(scene.emotions) or "None identified"))
            st.write("**Colors:** " + (", ".join(scene.colors) or "None identified"))

    st.divider()
    st.subheader("Hall–Van de Castle Coding")
    st.caption(
        "Evidence-based content labels for characters, interactions, activities, "
        "outcomes, emotions, settings, objects, and descriptive details. "
        "This is content coding, not dream interpretation."
    )
    if st.button("Code this dream", disabled=not MOCK_MODE and not live_consent):
        try:
            with st.spinner("Coding dream content…"):
                coding = code_dream(record)
                coding_path = save_dream_coding(
                    st.session_state["dream_session_id"], coding
                )
            st.session_state["dream_coding"] = coding
            st.session_state["dream_coding_path"] = str(coding_path)
        except RuntimeError as error:
            st.error(f"Could not code this dream. {error}")
        except Exception:
            st.error("Could not code this dream. The dream record remains saved locally.")

    coding = st.session_state.get("dream_coding")
    if coding is not None:
        st.write(coding.summary)
        st.caption(f"Coding file: {st.session_state['dream_coding_path']}")
        if coding.rows:
            st.dataframe(
                [row.model_dump() for row in coding.rows],
                hide_index=True,
                use_container_width=True,
            )
        elif MOCK_MODE:
            st.info("Mock mode returns no fabricated coding labels.")

    st.divider()
    st.subheader("Storyboard")
    st.caption(
        "Muse Image renders each scene from its structured description. "
        "Character descriptions are repeated across scene prompts for visual consistency."
    )
    style = st.text_input("Storyboard visual style", value="dreamlike cinematic illustration")
    storyboard = load_storyboard(st.session_state["dream_session_id"])
    if storyboard is None:
        if st.button("Generate storyboard", disabled=not MOCK_MODE and not live_consent):
            try:
                with st.spinner("Rendering storyboard scenes…"):
                    storyboard = generate_storyboard(
                        record, st.session_state["dream_session_id"], style
                    )
                    save_storyboard(st.session_state["dream_session_id"], storyboard)
                st.rerun()
            except RuntimeError as error:
                st.error(f"Could not generate the storyboard. {error}")
    else:
        st.session_state["storyboard"] = storyboard
        for frame in storyboard.frames:
            with st.expander(f"Scene {frame.scene_number}", expanded=True):
                current = frame.revisions[-1]
                st.caption(f"Revision {current.round_number}: {current.instruction}")
                if current.image_path and Path(current.image_path).exists():
                    st.image(current.image_path, use_container_width=True)
                elif MOCK_MODE:
                    st.info("Mock placeholder only; no image was generated.")
                if len(frame.revisions) > 1:
                    st.write("Revision history:")
                    for revision in frame.revisions[:-1]:
                        st.write(f"Round {revision.round_number}: {revision.instruction}")
                if frame.locked:
                    st.success("Scene approved and locked.")
                    if st.button("Unlock scene", key=f"unlock_{frame.scene_number}"):
                        frame.locked = False
                        save_storyboard(st.session_state["dream_session_id"], storyboard)
                        st.rerun()
                else:
                    correction = st.text_input(
                        "Correction for this scene",
                        key=f"correction_{frame.scene_number}",
                        disabled=MOCK_MODE or not live_consent,
                        placeholder="For example: make the lantern glow warmer",
                    )
                    left, right = st.columns(2)
                    with left:
                        if st.button(
                            "Apply correction",
                            key=f"refine_{frame.scene_number}",
                            disabled=MOCK_MODE or not live_consent or not correction.strip(),
                        ):
                            try:
                                updated = refine_storyboard_frame(
                                    storyboard,
                                    st.session_state["dream_session_id"],
                                    frame.scene_number,
                                    correction,
                                )
                                save_storyboard(st.session_state["dream_session_id"], updated)
                                st.rerun()
                            except RuntimeError as error:
                                st.error(str(error))
                    with right:
                        if st.button("That’s it · lock scene", key=f"lock_{frame.scene_number}"):
                            frame.locked = True
                            save_storyboard(st.session_state["dream_session_id"], storyboard)
                            st.rerun()
        if MOCK_MODE:
            st.info("Image generation and correction are disabled in mock mode.")
