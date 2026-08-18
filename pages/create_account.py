import streamlit as st
import base64

from pathlib import Path
from tools.authentication import create_account

register_icon = Path(__file__).parent.parent / "assets" / "images" / "0001.png" 

def b64_image(filepath, width):
    with open(filepath, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    st.markdown(
        f'<div style="text-align: center; padding-bottom: 16px;"><img src="data:image/png;base64,{b64}" width="{width}"></div>',
        unsafe_allow_html=True
    )


def render():
    with st.container(horizontal=True, horizontal_alignment="center"):
        with st.container(width=400):
            # st.markdown(
            #     "<h1 style='text-align: center;'>Create Account</h1>",
            #     unsafe_allow_html=True
            # )
            b64_image(register_icon, 120)
            with st.form(key="add_account", border=True):
                email = st.text_input("Email")
                username = st.text_input("Username")
                pw = st.text_input("Password", type="password")
                confirm_pw = st.text_input("Confirm Password", type="password")
                submit_btn = st.form_submit_button("Create", width="stretch", type="primary")
                
                if submit_btn:
                    if not email or not username or not pw or not confirm_pw:
                        st.warning("All fields are required")
                    elif pw != confirm_pw:
                        st.error("Password not match")
                    elif '@' not in email:
                        st.warning("Email not valid")
                    else:
                        status = create_account(username, email, pw)
                        if status == "success":
                            st.session_state["account_creation"] = username
                            st.switch_page(login_page)
                        elif status == "username":
                            st.error("Username already exist")
                        elif status == "email":
                            st.error("Email already exist")
                        else:
                            st.error("Unknown error has occurred")
            st.markdown(
                "<p style='text-align: center; font-size: 0.85rem;'>Already have an account?</p>",
                unsafe_allow_html=True
            )
            with st.container(horizontal=True, horizontal_alignment="center"):
                from app import login_page
                st.page_link(login_page, label="Login")
