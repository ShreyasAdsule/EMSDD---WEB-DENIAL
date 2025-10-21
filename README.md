# Secure Flask Web Application

A demo security-focused web application using Flask. Includes authentication, rate limiting, password management, profile editing, secure messaging, logging, and user activity audit trail.

## Features

- Secure login with hashed password and CAPTCHA
- Account lockout on repeated failed logins
- Change password (dashboard link)
- Profile editing ("About Me" field)
- Contact Admin messaging from dashboard
- Rate limiting for login and service requests
- Role-based access (user/admin)
- System logs and message logs for admin
- User activity timeline (audit trail)
- Admin view of any user's activity timeline
- In-memory storage for demo purposes

## Quick Start

1. Install required packages:
    ```
    pip install flask flask-limiter werkzeug
    ```
2. Place all `.html` files in the `templates/` directory.
3. Run:
    ```
    python app.py
    ```
4. Access at [http://localhost:5000](http://localhost:5000)

## Default Users

- user1 / pass1 (regular user)
- admin / adminpass (admin role)

## Notes

- For real-world use: Add persistent database, use environment variables for secret keys, secure sessions, implement 2FA/SSL.
- All audit and log trails are reset when app restarts.

## License

MIT
