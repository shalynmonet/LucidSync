"""A separate, user-approved imagined rewrite; original dream records are retained."""
import json
from pathlib import Path


def render_nightmare_tab():
    import streamlit as st
    from meta_client import MOCK_MODE, rewrite_nightmare, structure_dream, generate_storyboard
    from storage import save_dream_record, save_storyboard

    st.header("Imagine a safer ending")
    st.info("A rehearsal support tool to use alongside a clinician. This is not treatment or a medical device and does not diagnose.")
    st.caption("Content warning: recalling a nightmare may be distressing. You choose the ending and approve the text before any images are made.")
    if MOCK_MODE:
        st.info("Mock mode: local alternative-text and storyboard placeholders; no Meta requests.")
    original = st.text_area("Nightmare to rewrite", key="rewrite_original", height=150)
    ending = st.text_area("My preferred safer ending (optional)", key="rewrite_ending",
                          placeholder="Write an ending you want, or leave blank to request a suggestion.")
    consent = MOCK_MODE or st.checkbox("Send this nightmare and ending to Meta to draft the alternative story and, if I approve it, generate images.")
    if st.button("Prepare alternative story", disabled=not original.strip() or not consent):
        try:
            with st.spinner("Drafting a story for your review…"):
                narrative = rewrite_nightmare(original, ending)
            st.session_state["rewrite_draft"] = {"original": original, "ending": ending, "narrative": narrative}
            st.session_state.pop("rewrite_board", None)
            st.session_state.pop("rewrite_approval", None)
        except Exception:
            st.error("Could not prepare the alternative story. Your original dream records are unchanged.")
    draft = st.session_state.get("rewrite_draft")
    if draft and (draft["original"] != original or draft["ending"] != ending):
        st.info("The inputs changed. Prepare a new alternative story to continue.")
        return
    if draft:
        st.subheader("Review the imagined story")
        # Edits are local and become authoritative for the rendered storyboard.
        reviewed = st.text_area("Edit the alternative story", value=draft["narrative"], key="reviewed_" + str(hash(draft["narrative"])), height=180)
        approved = st.checkbox("I have reviewed this alternative story and want to illustrate it", key="rewrite_approval")
        if st.button("Create rehearsal storyboard", disabled=not approved or not consent or not reviewed.strip()):
            try:
                with st.spinner("Rendering the approved alternative story…"):
                    record = structure_dream(reviewed, "not supplied", 3)
                    sid, path = save_dream_record(record)
                    metadata = {"kind": "imagined_nightmare_rewrite", "original_report": original,
                                "preferred_ending": ending, "approved_narrative": reviewed,
                                "mock": MOCK_MODE}
                    (path.parent / "rewrite.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
                    board = generate_storyboard(record, sid, "gentle, non-graphic illustrated storyboard")
                    save_storyboard(sid, board)
                st.session_state["rewrite_board"] = {"board": board, "session": sid, "narrative": reviewed}
            except Exception:
                st.error("Could not render the alternative storyboard. Your original dream records are unchanged.")
        rendered = st.session_state.get("rewrite_board")
        if rendered and rendered["narrative"] == reviewed:
            st.caption(f"Separate imagined-rewrite session: {rendered['session']}")
            for frame in rendered["board"].frames:
                st.write(f"Scene {frame.scene_number}")
                image = frame.revisions[-1].image_path
                if image and Path(image).exists():
                    st.image(image)
                else:
                    st.info("Mock storyboard placeholder; no image was generated.")
