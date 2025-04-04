import streamlit as st
import auth

def app():
    auth.init_auth()
    
    st.title("Sign Up")
    
    # Check if user is already logged in
    if auth.is_authenticated():
        st.success(f"Already logged in as {st.session_state['username']}")
        if st.button("Logout"):
            auth.logout()
            st.experimental_rerun()
        return
    
    # Signup form
    with st.form("signup_form"):
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password", help="Password must be at least 8 characters long, include at least one uppercase letter and one number")
        confirm_password = st.text_input("Confirm Password", type="password")
        submit_button = st.form_submit_button("Sign Up")
        
        if submit_button:
            if not username or not email or not password or not confirm_password:
                st.error("Please fill in all fields")
            elif not auth.is_valid_email(email):
                st.error("Please enter a valid email address")
            elif not auth.is_valid_password(password):
                st.error("Password must be at least 8 characters long, include at least one uppercase letter and one number")
            elif password != confirm_password:
                st.error("Passwords do not match")
            else:
                if auth.add_user(username, email, password):
                    st.success("Account created successfully! You can now login.")
                    st.session_state['username'] = username
                    st.session_state['authentication_status'] = True
                    st.experimental_rerun()
                else:
                    st.error("Username or email already exists")
    
    # Link to login page
    st.write("Already have an account? [Login](/login)")
