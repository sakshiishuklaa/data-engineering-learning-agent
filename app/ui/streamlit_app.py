"""Module 0 Streamlit entry point."""

import streamlit as st

from app.config import get_settings
from app.logging_config import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

st.set_page_config(page_title=settings.app_name, page_icon="🎓")
st.title("Data Engineering Learning Coach")
st.caption("Module 0 — project foundation")
st.info("The learning coach interface will be introduced in a future module.")
st.write(f"Environment: `{settings.environment}`")
