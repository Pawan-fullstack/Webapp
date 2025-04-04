import streamlit as st
import sqlite3
import hashlib
import re
from datetime import datetime

# Initialize connection to SQLite database
def init_connection():
    return sqlite3.connect('users.db', check_same_thread=False)

# Create users table if it doesn't exist
def create_users_table():
    conn = init_connection()
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()

# Hash password
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# Check password against hash
def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return True
    return False

# Add user to database
def add_user(username, email, password):
    conn = init_connection()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (username, email, password, created_at) VALUES (?, ?, ?, ?)',
                  (username, email, make_hashes(password), datetime.now()))
        conn.commit()
        result = True
    except sqlite3.IntegrityError:
        result = False
    conn.close()
    return result

# Login verification
def login_user(username, password):
    conn = init_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    
    if data:
        user_id, db_username, db_email, db_password, db_created_at = data
        return check_hashes(password, db_password)
    return False

# Get user data
def get_user_data(username):
    conn = init_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    data = c.fetchone()
    conn.close()
    
    if data:
        user_id, db_username, db_email, db_password, db_created_at = data
        return {"id": user_id, "username": db_username, "email": db_email, "created_at": db_created_at}
    return None

# Email validation
def is_valid_email(email):
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email))

# Password validation (min 8 chars, at least one number and one uppercase)
def is_valid_password(password):
    if len(password) < 8:
        return False
    if not any(char.isdigit() for char in password):
        return False
    if not any(char.isupper() for char in password):
        return False
    return True

# Check if user is logged in
def is_authenticated():
    return 'username' in st.session_state and st.session_state['username'] is not None

# Initialize authentication
def init_auth():
    # Create database tables if they don't exist
    create_users_table()
    
    # Initialize session state variables
    if 'username' not in st.session_state:
        st.session_state['username'] = None
    if 'authentication_status' not in st.session_state:
        st.session_state['authentication_status'] = None

# Logout user
def logout():
    st.session_state['username'] = None
    st.session_state['authentication_status'] = None
