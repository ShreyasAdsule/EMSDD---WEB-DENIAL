# app.py

import os
import secrets
import random
import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
from functools import wraps
import time

from db import db, User, Message

load_dotenv()


# Context variables for rate-limiting
failed_attempts = {}
LOCKOUT_MINUTES = 5


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_SESSION_KEY', 'replace-this-in-prod')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,  # Use True in production
    SESSION_COOKIE_SAMESITE='Lax'
)

SESSION_TIMEOUT_MINUTES = 30

from datetime import datetime, timedelta

from datetime import datetime, timedelta, timezone

def log_event(user, event_type, event_data=""):
    from db import SecurityEvent
    db.session.add(SecurityEvent(user_id=user.id, event_type=event_type, event_data=event_data))
    db.session.commit()


def is_session_expired():
    last_active = session.get('last_active')
    now = datetime.now(timezone.utc)  # timezone-aware

    if last_active and now - last_active > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
        return True

    session['last_active'] = now  # store timezone-aware datetime
    return False



db.init_app(app)
csrf = CSRFProtect(app)

def current_user():
    uid = session.get('user_id')
    token = session.get('session_token')
    if not uid or not token:
        return None
    user = User.query.get(uid)
    if user and user.session_token == token:
        return user
    return None

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = current_user()
            if not user or user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# @app.before_first_request
# def create_tables():
#     db.create_all()

@app.context_processor
def inject_user():
    return {"current_user": current_user()}

@app.route('/')
def home():
    user = current_user()
    return render_template('home.html', user=user)

import random

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        captcha_answer = request.form.get('captcha')
        correct_answer = session.get('captcha_answer')

        # 1. CAPTCHA validation
        if captcha_answer != correct_answer:
            flash("Captcha failed.", "danger")
            return render_template('register.html', captcha_question=session.get('captcha_question'))

        # 2. Check if username or email taken
        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            flash("Username or email already taken", "danger")
            return render_template('register.html', captcha_question=session.get('captcha_question'))

        # 3. Create and save the user
        user = User(username=username, email=email, role='user')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))
    
    # GET request: generate and store new random math CAPTCHA
    a = random.randint(1, 10)
    b = random.randint(1, 10)
    session['captcha_question'] = f"{a} + {b}"
    session['captcha_answer'] = str(a + b)
    return render_template('register.html', captcha_question=session['captcha_question'])




@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        # (1) Check for account lockout
        if user and user.locked_until:
            now = datetime.datetime.utcnow()
            if now < user.locked_until:
                flash('Account locked. Please try again later.', 'danger')
                log_event(user, "LoginFailed", f"IP={request.remote_addr}")
                return render_template('login.html')

        # (2) Check password
        if user and user.check_password(password):
            # Reset failed attempts and clear lockout on success
            failed_attempts[username] = 0
            user.locked_until = None
            db.session.commit()
            token = secrets.token_hex(32)
            user.session_token = token
            db.session.commit()
            session['user_id'] = user.id
            session['session_token'] = token
            flash('Login successful!', 'success')
            log_event(user, "LoginSuccess", f"IP={request.remote_addr}")
            return redirect(url_for('dashboard'))
        else:
            # (3) Increment failed attempts
            failed_attempts[username] = failed_attempts.get(username, 0) + 1
            # Lock out if 5 or more failures
            if failed_attempts[username] >= 5 and user:
                user.locked_until = datetime.datetime.utcnow() + datetime.timedelta(minutes=LOCKOUT_MINUTES)
                db.session.commit()
                flash('Account locked after too many attempts. Please try again in 5 minutes.', 'danger')
                log_event(user, "LoginFailed", f"IP={request.remote_addr}")
            else:
                flash('Invalid credentials.', 'danger')
                log_event(user, "LoginFailed", f"IP={request.remote_addr}")

    return render_template('login.html')

@app.route('/logout')
def logout():
    if is_session_expired():
        session.clear()
        flash('Your session has expired. Please log in again.', 'warning')
        return redirect(url_for('login'))
    user = current_user()
    if user:
        user.session_token = None
        db.session.commit()
    session.clear()
    flash('Logged out!', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if is_session_expired():
        session.clear()
        flash('Your session has expired. Please log in again.', 'warning')
        return redirect(url_for('login'))
    user = current_user()
    if not user:
        return redirect(url_for('login'))
    events = sorted(user.security_events, key=lambda e: e.timestamp, reverse=True)[:10]
    return render_template('dashboard.html', user=user, events=events)

@app.route('/admin')
@role_required('admin')
def admin():
    if is_session_expired():
        session.clear()
        flash('Your session has expired. Please log in again.', 'warning')
        return redirect(url_for('login'))
    users = User.query.all()
    return render_template('admin.html', users=users)

@app.route('/admin/events')
@role_required('admin')  # Make sure this decorator enforces admin-only access
def all_events():
    from db import SecurityEvent, User  # adjust import if needed
    # Query all events, sorted by most recent
    events = SecurityEvent.query.order_by(SecurityEvent.timestamp.desc()).all()
    # You may also want to include associated user data for display
    return render_template('all_events.html', events=events)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    user = current_user()
    if not user:
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_email = request.form.get('email')
        current_pwd = request.form.get('current_password')
        new_pwd = request.form.get('new_password')

        # Must enter current password for any change
        if not current_pwd or not user.check_password(current_pwd):
            flash('Current password incorrect—cannot update details.', 'danger')
            return render_template('profile.html', user=user)

        # Update email if changed
        if new_email and new_email != user.email:
            if User.query.filter_by(email=new_email).first():
                flash('That email is already in use by another user.', 'danger')
            else:
                user.email = new_email
                flash('Email updated.', 'success')

        # Update password if provided and non-empty
        if new_pwd and new_pwd.strip():
            user.set_password(new_pwd.strip())
            flash('Password updated.', 'success')

        db.session.commit()
        # Reload current user state
        user = User.query.get(user.id)

    return render_template('profile.html', user=user)

from flask import request, session, redirect, url_for, render_template, flash

@app.route('/messages', methods=['GET', 'POST'])
def messages():
    user = current_user()
    if not user:
        return redirect(url_for('login'))

    if request.method == 'POST':
        recipient_username = request.form['recipient']
        content = request.form['content']
        recipient = User.query.filter_by(username=recipient_username).first()
        if recipient and recipient.id != user.id and content.strip():
            msg = Message(sender_id=user.id, recipient_id=recipient.id, content=content.strip())
            db.session.add(msg)
            db.session.commit()
            flash('Message sent!', 'success')
        else:
            flash('Invalid recipient or empty message.', 'danger')

    # Show received messages (inbox)
    inbox = Message.query.filter_by(recipient_id=user.id).order_by(Message.timestamp.desc()).all()
    users = User.query.all()  # So you can select a recipient in the form
    return render_template('messages.html', inbox=inbox, users=users)


# Custom error pages for better UX/design
@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

def create_tables():
    with app.app_context():
        db.create_all()
