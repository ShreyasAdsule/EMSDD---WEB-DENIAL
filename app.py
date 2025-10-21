from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
import random, time
from collections import defaultdict, deque

app = Flask(__name__)
app.secret_key = 'your_secret_key'

limiter = Limiter(get_remote_address, app=app, default_limits=["10 per minute"])

users = {
    "user1": generate_password_hash("pass1"),
    "admin": generate_password_hash("adminpass")
}
user_roles = {
    "user1": "user",
    "admin": "admin"
}

profiles = defaultdict(str)  # For profile "about me" info
messages_to_admin = deque(maxlen=100)  # For contact messages

failed_attempts = defaultdict(int)
locked_accounts = {}
request_logs = deque(maxlen=10000)
blocked_ips = set()
user_activity = defaultdict(lambda: deque(maxlen=200))  # Audit trail

def generate_captcha():
    a, b = random.randint(1, 9), random.randint(1, 9)
    session['captcha_answer'] = str(a + b)
    session['captcha_q'] = f"{a} + {b}"
    return session['captcha_q']

def check_account_locked(username):
    if username in locked_accounts and time.time() < locked_accounts[username]:
        return True
    elif username in locked_accounts:
        del locked_accounts[username]
        failed_attempts[username] = 0
    return False

@app.before_request
def before_request():
    client_ip = get_remote_address()
    if client_ip in blocked_ips:
        return "Access denied - IP blocked.", 403

@app.route('/', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        captcha_response = request.form['captcha']
        captcha_answer = session.get('captcha_answer')
        captcha_q = session.get('captcha_q', '???')

        if check_account_locked(username):
            flash(f"Account locked. Try again later.")
            return render_template('login.html', captcha_q=captcha_q)
        if username in users and check_password_hash(users[username], password):
            if captcha_response == captcha_answer:
                session['username'] = username
                failed_attempts[username] = 0
                user_activity[username].appendleft({'event': 'login', 'time': time.strftime('%Y-%m-%d %H:%M:%S')})
                print(user_activity)
                return redirect(url_for('dashboard'))
            else:
                flash("CAPTCHA verification failed.")
        else:
            failed_attempts[username] += 1
            if failed_attempts[username] >= 3:
                locked_accounts[username] = time.time() + 60
            flash("Incorrect username or password.")
        return render_template('login.html', captcha_q=captcha_q)
    captcha_q = generate_captcha()
    return render_template('login.html', captcha_q=captcha_q)

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    role = user_roles.get(username, 'user')
    about_me = profiles.get(username, "")
    return render_template('dashboard.html', username=username, role=role, about_me=about_me)

@app.route('/request_service', methods=['POST'])
@limiter.limit("3 per minute")
def request_service():
    if 'username' not in session:
        return "User not logged in.", 401
    request_logs.append({'timestamp': time.time(), 'event': 'service_request', 'username': session['username']})
    user_activity[session['username']].appendleft({'event': 'service_request', 'time': time.strftime('%Y-%m-%d %H:%M:%S')})
    return "Service request processed and logged!"

@app.route('/view_logs')
def view_logs():
    if 'username' not in session or user_roles.get(session['username']) != 'admin':
        return "Not authorized", 403
    return render_template('logs.html', logs=list(request_logs)[-100:], messages=list(messages_to_admin))

@app.route('/logout')
def logout():
    if 'username' in session:
        user_activity[session['username']].appendleft({'event': 'logout', 'time': time.strftime('%Y-%m-%d %H:%M:%S')})
    session.clear()
    return redirect(url_for('login'))

# --- Profile About Me Feature ---
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    if request.method == 'POST':
        about_me = request.form.get('about_me', '')
        profiles[username] = about_me
        flash("Profile updated.")
        user_activity[username].appendleft({'event': 'profile_edit', 'time': time.strftime('%Y-%m-%d %H:%M:%S')})
    return render_template('profile.html', username=username, about_me=profiles.get(username, ""))

# --- Change Password Feature ---
@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    if request.method == 'POST':
        old_pw = request.form['old_password']
        new_pw = request.form['new_password']
        if check_password_hash(users[username], old_pw):
            users[username] = generate_password_hash(new_pw)
            flash("Password changed successfully.")
            user_activity[username].appendleft({'event': 'password_changed', 'time': time.strftime('%Y-%m-%d %H:%M:%S')})
            return redirect(url_for('dashboard'))
        else:
            flash("Old password incorrect.")
    return render_template('change_password.html')

# --- Contact Admin Feature ---
@app.route('/contact_admin', methods=['GET', 'POST'])
def contact_admin():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    if request.method == 'POST':
        message = request.form['message']
        messages_to_admin.append({'user': username, 'msg': message, 'time': time.strftime('%Y-%m-%d %H:%M')})
        flash("Message sent to admin!")
        user_activity[username].appendleft({'event': 'contact_admin', 'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'msg': message})
        return redirect(url_for('dashboard'))
    return render_template('contact_admin.html')

# --- Activity Timeline ---
@app.route('/activity')
def activity():
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    entries = list(user_activity[username])
    return render_template('activity.html', entries=entries, show_user=None)

@app.route('/user_activity', methods=['GET', 'POST'])
def user_activity_admin():
    if 'username' not in session or user_roles.get(session['username']) != 'admin':
        return redirect(url_for('login'))
    entries = []
    user_to_show = None

    # Handle POST forms and GET query parameters
    if request.method == 'POST':
        user_to_show = request.form['username'].strip()
    elif request.method == 'GET':
        user_to_show = request.args.get('username', '').strip()

    if user_to_show:
        if user_to_show in user_activity and user_activity[user_to_show]:
            entries = list(user_activity[user_to_show])
        else:
            flash(f"No activity found for user '{user_to_show}'.")
    return render_template('activity.html', entries=entries, show_user=user_to_show)


if __name__ == '__main__':
    app.run(debug=True)
