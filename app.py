"""LucidSync's first milestone: a small Streamlit scaffold."""

import streamlit as st

st.set_page_config(page_title="LucidSync", page_icon="🌙", layout="centered")

st.title("LucidSync")
st.write(
    "Turn a morning dream memory into structured, visualized, and labeled data."
)
st.info(
    "Research and wellness tool, not a medical device. LucidSync does not diagnose."
)

st.subheader("Project scaffold")
st.write(
    "Milestone 1 is ready. The next milestone will add dream capture and structured records."
)
