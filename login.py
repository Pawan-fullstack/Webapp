import streamlit as st
import auth

def app():
    auth.init_auth()
    
    st.title("Login")
    
    # Check if user is already logged in
    if auth.is_authenticated():
        st.success(f"Logged in as {st.session_state['username']}")
        if st.button("Logout"):
            auth.logout()
            st.experimental_rerun()
        return
    
    # Login form
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")
        
        if submit_button:
            if not username or not password:
                st.error("Please fill in all fields")
            else:
                if auth.login_user(username, password):
                    st.session_state['username'] = username
                    st.session_state['authentication_status'] = True
                    st.success("Login successful!")
                    st.experimental_rerun()
                else:
                    st.error("Invalid username or password")
    
    # Link to signup page
    st.write("Don't have an account? [Sign up](/signup)")
