from pathlib import Path
import streamlit as st
import base64

from tools.authentication import login
from tools.auth_session import persist_login

login_icon = Path(__file__).parent.parent / "assets" / "images" / "0025.png" 

def b64_image(filepath, width):
    with open(filepath, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    st.markdown(
        f'<div style="text-align: center; padding-bottom: 16px;"><img src="data:image/png;base64,{b64}" width="{width}"></div>',
        unsafe_allow_html=True
    )

def render() -> None:
    with st.container(horizontal=True, horizontal_alignment="center"):
        with st.container(width=400):
            with st.container(horizontal_alignment="center"):
                b64_image(login_icon, 120)
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

            st.markdown(
                "<p style='text-align: center; font-size: 0.85rem;'>Don't have an account?</p>", 
                unsafe_allow_html=True
            )
            with st.container(horizontal=True, horizontal_alignment="center"):
                from app import register_page
                st.page_link(register_page, label="Create an account")

            if new_user := st.session_state.pop("account_creation", None):
                st.toast(f"@{new_user} created!", icon="🟢")
                st.balloons()

            # if create_btn:
            #     from web.app import register_page
            #     st.switch_page(register_page)
