import streamlit as st

from utils import gate_access, is_admin, build_nav_pages

# Determine who's logged in (and whether they're approved) before building
# the navigation menu, so we know whether to include the Dashboard page.
user_record = gate_access()
viewer_is_admin = is_admin(user_record)

pages = build_nav_pages(viewer_is_admin)
st.session_state["nav_pages"] = pages

# Floating widget buttons (e.g. the cart icon) are plain <a href="?goto=...">
# links rather than real Streamlit page links, since they're injected via
# raw HTML/JS outside Streamlit's own component tree. This runs first, on
# every single page load, to translate that query param into a real
# st.switch_page() before any page content renders.
goto = st.query_params.get("goto")
if goto:
    st.query_params.clear()
    goto_page_map = {
        "cart": "pages/2_Cart.py",
        "catalog": "pages/1_Catalog.py",
        "showcase": "pages/4_Showcase.py",
        "orders": "pages/3_Order_History.py",
    }
    target_page = goto_page_map.get(goto)
    if target_page:
        st.switch_page(target_page)

# "hidden" — we render our own professional navbar (logo + links + user +
# logout) inside each page via render_top_navbar(), instead of Streamlit's
# built-in nav widget.
pg = st.navigation(pages, position="hidden")
pg.run()
