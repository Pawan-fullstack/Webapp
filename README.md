# Stock Pondering App

A Streamlit-based web application for stock analysis with user authentication.

## Features

- User authentication system (signup, login, logout)
- Stock analysis tools
- Interactive charts and visualizations
- Secure password storage with hashing
- User profile management

## Installation

1. Clone this repository:
```
git clone <repository-url>
cd stock-pondering-app
```

2. Install required packages:
```
pip install -r requirements.txt
```

3. Run the application:
```
streamlit run main.py
```

## Project Structure

```
stock-pondering-app/
├── main.py              # Main application entry point
├── auth.py              # Authentication module
├── login.py             # Login page
├── signup.py            # Signup page
├── home.py              # Home page
├── requirements.txt     # Required packages
└── users.db             # SQLite database (created on first run)
```

## Authentication System

The app uses a custom authentication system built on:
- SQLite for database storage
- SHA-256 hashing for password security
- Session state management with Streamlit

## Usage

1. Create an account via the signup page
2. Log in with your credentials
3. Access stock analysis tools and personalized features
4. Use the sidebar navigation to move between pages

## Security Features

- Password hashing with SHA-256
- Email validation
- Strong password requirements
- Protection against SQL injection
- Authentication status checking for protected routes

## Customization

You can customize the authentication system by modifying `auth.py`. Available options include:
- Changing password requirements
- Adding additional user fields
- Implementing email verification
- Adding password reset functionality
