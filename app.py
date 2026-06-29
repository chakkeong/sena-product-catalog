import streamlit as st

from utils import gate_access, is_admin, build_nav_pages

# Determine who's logged in (and whether they're approved) before building
# the navigation menu, so we know whether to include the Dashboard page.
user_record = gate_access()
viewer_is_admin = is_admin(user_record)

pages = build_nav_pages(viewer_is_admin)
st.session_state["nav_pages"] = pages

# "hidden" — we render our own professional navbar (logo + links + user +
# logout) inside each page via render_top_navbar(), instead of Streamlit's
# built-in nav widget.
pg = st.navigation(pages, position="hidden")
pg.run()
