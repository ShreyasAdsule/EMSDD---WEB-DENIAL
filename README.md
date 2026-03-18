# Secure Flask Web Application

A robust, full-featured Flask web platform designed for modern security—as well as user convenience, messaging, auditability, and administration.  
**Database**: Powered by [Neon](https://neon.tech/) (cloud PostgreSQL).

---

## Table of Contents

1. [Overview](#overview)
2. [Key Features](#key-features)
3. [Security Architecture](#security-architecture)
4. [Prerequisites](#prerequisites)
5. [Setup & Installation](#setup--installation)
6. [Configuration](#configuration)
7. [Running the Application](#running-the-application)
8. [Usage Guide](#usage-guide)
9. [Development Notes](#development-notes)
10. [Contributing](#contributing)
11. [License & Contact](#license--contact)

---

## Overview

This application demonstrates a best-practice approach to user authentication, account management, in-app messaging, and operational audit logging—ideal for secure web environments and demo platforms alike.

---

## Key Features

- **User Registration**  
  - Secure sign-up with dynamic math CAPTCHA to block bots
- **Email Verification** *(extend as needed)*
- **Login Security**  
  - Account lockout on repeated failed login attempts (rate-limiting)
  - Audit logging for both successful and failed logins (IP-based)
- **Session Timeout Handling**  
  - Auto logout after inactivity
- **User Dashboard**  
  - View profile and recent security events
- **User Profile Management**  
  - Edit email and password, with password verification required
- **Messaging System**  
  - Send/receive messages with other users (secure inbox)
- **Admin Features**  
  - View all registered users
  - View all security events for all users (audit log)
- **Role-Based Access Control**  
  - Admin/user separation at the route level (decorators)
- **Custom Error Pages**  
  - Friendly 403 and 404 pages

---

## Security Architecture

- **Password Storage:** All user passwords are securely hashed and salted
- **CSRF Protection:** All forms leverage Flask-WTF’s CSRF tokens
- **CAPTCHA Enforcement:** Prevents automated/bot registrations
- **Rate-Limited Login:** Five consecutive failed login attempts lead to a timed account lockout
- **Strict Session Controls:** Short-lived, secure, HTTP-only cookies; inactivity-based expiration
- **Audit Logging:** Every login, logout, failed attempt, and data change is recorded with timestamp, type, and IP
- **Admin Oversight:** Administrators can view all activity, not just their own

---

## Prerequisites

- **Python**: 3.8 or later
- **PostgreSQL**: Neon DB account ([signup](https://neon.tech/))
- **SMTP Account**: For email notifications (Gmail, Outlook, etc.)
- **Python Packages:**  
  (See `requirements.txt`)
    - Flask
    - Flask-SQLAlchemy
    - Flask-WTF
    - Flask-Mail
    - Flask-Talisman
    - python-dotenv
    - psycopg2-binary
    - pyotp

---

## Setup & Installation

1. **Clone the Repository**
    ```
    git clone <your-repo-url>
    cd web_denial_updated
    ```

2. **Create a Python Virtual Environment**
    ```
    python -m venv venv
    source venv/bin/activate   # Windows: venv\Scripts\activate
    ```

3. **Install Dependencies**
    ```
    pip install -r requirements.txt
    ```

4. **Configure Environment Variables**
    - Copy `.env.example` to `.env` and enter:
        ```
        SECRET_SESSION_KEY=your-secure-secret-key
        DATABASE_URL=postgresql+psycopg2://<user>:<password>@<neon-host>/<db>
        MAIL_SERVER=smtp.gmail.com
        MAIL_PORT=587
        MAIL_USE_TLS=True
        MAIL_USERNAME=your_email@gmail.com
        MAIL_PASSWORD=your_gmail_app_password
        MAIL_DEFAULT_SENDER=your_email@gmail.com
        ```

---

## Configuration

- **Database:** Hosted on Neon for cloud reliability.
- **Mail Server:** Configure SMTP credentials for automated email notifications, verification.
- **Security Settings:**  
    Environment variables define session secrets, mail, and DB connections.
- **Session Management:**  
    HTTP-only, SameSite=Lax, Secure cookies.

---

## Running the Application

1. **Initialize Database Tables (First Run)**
    ```
    from app import db, app
    with app.app_context():
        db.create_all()
    ```

2. **Launch the Server**
    ```
    flask run
    # or
    python app.py
    ```

3. **Visit in Browser:**  
    ```
    http://127.0.0.1:5000
    ```

---

## Usage Guide

**User Journey:**
- Register (dynamic CAPTCHA; unique email/username required)
- Receive verification email (optional)
- Log in with password (lockout on repeated failures)
- View your dashboard for profile and recent security events
- Edit your profile (secure, current password required to change any sensitive info)
- Send & receive secure messages with other users
- Log out and auto-logout on inactivity

**Admin Journey:**
- Log in as an admin
- View/manage all users (`/admin`)
- View full audit event log for all accounts (`/admin/events`)

---

## Development Notes

- **Security:**  
    All forms implement CSRF tokens, input validation.
- **Sessions:**  
    Session expiry and login tokens managed strictly.
- **Audit Events:**  
    Every critical action is logged; admins view all.
- **Database:**  
    All models are extensible for further fields/features.

---

## Contributing

Pull requests and suggestions are **welcomed**!  
Please follow best practices and open an issue for major changes.

---

## License & Contact

This project is licensed under the MIT License.  
Questions, issues, or feature requests? Contact [your-email@example.com]

## Contributors

- Dhanalakshmi Parthipan  
- Penamareddy Eshwar Adharsh Reddy
- Shreyas Adsule
- Shreyas Adsule
- Mohit Naidu Ganisetti
- Derrick Dabreo

---

**Last updated:** November 25, 2025
