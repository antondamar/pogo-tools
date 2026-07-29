import streamlit as st

from dashboard import login
from web.auth_session import persist_login


def render() -> None:
    try:
        with st.container(horizontal=True, horizontal_alignment="center"):
            with st.container(width=400):
                st.markdown(
                    "<h1 style='text-align: center;'>Login</h1>",
                    unsafe_allow_html=True,
                )
                with st.form(key="login"):
                    username = st.text_input("Username")
                    password = st.text_input("Password", type="password")

                    submit_button = st.form_submit_button("Login", width="stretch", type="primary")
                    if submit_button:
                        if not username or not password:
                            st.warning("All fields are required")
                        else:
                            login_status = login(username, password)
                            if isinstance(login_status, str) and login_status.startswith("Error"):
                                st.warning(login_status)
                            elif login_status:
                                persist_login(login_status[0], login_status[1])
                                st.rerun()
                            else:
                                st.warning("Username/Password not valid.")
                with st.container(horizontal_alignment="center"):
                    create_btn = st.button("Create a new account", width=180)

                if new_user := st.session_state.pop("account_creation", None):
                    st.toast(f"@{new_user} created!", icon="🟢")
                    st.balloons()

                if create_btn:
                    from web.app import register_page
                    st.switch_page(register_page)
    except Exception as e:
        st.error(str(e))
