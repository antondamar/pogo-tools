import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from web.auth_session import clear_login, restore_user
from web.pages import auth, create_account, dashboard


login_page = st.Page(auth.render, title="Login", url_path="login", default=True)
register_page = st.Page(create_account.render, title="Create Account", url_path="register")

def run_app() -> None:
    st.set_page_config(page_title="Pokemon Go Tools", layout="wide")

    restore_user()

    if "user" not in st.session_state:
        pages = [
            login_page,
            register_page
        ]
    else:
        pages = [
            st.Page(dashboard.render, title="Dashboard", url_path="dashboard", default=True)
        ]

    pg = st.navigation(pages, position="hidden")
    pg.run()

    if "user" in st.session_state:
        with st.sidebar:
            st.caption(f"Signed in as @{st.session_state['user']['username']}")
            if st.button("Logout", width="stretch"):
                clear_login()
                st.rerun()


if __name__ == "__main__":
    run_app()
