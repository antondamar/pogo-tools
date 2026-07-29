import streamlit as st

from dashboard import create_account


def render():
    with st.container(horizontal=True, horizontal_alignment="center"):
        with st.container(width=400):
            st.markdown(
                "<h1 style='text-align: center;'>Create Account</h1>",
                unsafe_allow_html=True
            )
            with st.form(key="add_account", border=True):
                email = st.text_input("Email")
                username = st.text_input("Username")
                pw = st.text_input("Password", type="password")
                confirm_pw = st.text_input("Confirm Password", type="password")
                submit_btn = st.form_submit_button("Create", width="stretch")
                
                if submit_btn:
                    if pw != confirm_pw:
                        st.error("Password not match")
                    elif not email or not username or not pw or not confirm_pw:
                        st.warning("All fields are required")
                    elif '@' not in email:
                        st.warning("Email not valid")
                    else:
                        status = create_account(username, email, pw)
                        if status == "success":
                            st.session_state["account_creation"] = username
                            from web.app import login_page
                            st.switch_page(login_page)
                        elif status == "username":
                            st.error("Username already exist")
                        elif status == "email":
                            st.error("Email already exist")
                        else:
                            st.error("Unknown error has occurred")
