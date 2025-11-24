from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
import random
import smtplib
import time
import threading
from collections import defaultdict, deque
import json
from datetime import datetime, timedelta
import hashlib
import socket
import os

from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'your_secret_key_change_in_production'

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://neondb_owner:npg_i4LImJW7eOUv@ep-bold-sound-ah5jadlt-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'  # set in heroku, railway, or locally via .env
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Enhanced Rate Limiter with Redis-like functionality
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Security Configuration
SECURITY_CONFIG = {
    'max_failed_attempts': 3,
    'lockout_duration': 300,  # 5 minutes
    'dos_threshold': 100,     # requests per minute
    'ddos_threshold': 1000,   # total requests per minute
    'suspicious_patterns': ['admin', 'login', 'sql', 'script', 'union']
}


db = SQLAlchemy(app)


# Defining user model combining User and User_Role together

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(80), nullable=False)

# Enhanced user database with hashed passwords
users = {
    "user1": generate_password_hash("pass1"),
    "admin": generate_password_hash("adminpass"),
    "security_admin": generate_password_hash("secpass123")
}

user_roles = {
    "user1": "user", 
    "admin": "admin", 
    "security_admin": "security_admin"
}

# Security monitoring data structures
failed_attempts = defaultdict(int)
locked_accounts = {}
request_logs = deque(maxlen=10000)
attack_logs = []
ip_requests = defaultdict(lambda: deque(maxlen=1000))
blocked_ips = set()
security_alerts = []

# DoS/DDoS Detection System
class SecurityMonitor:
    def __init__(self):
        self.reset_counters()
        
    def reset_counters(self):
        self.current_minute = int(time.time() // 60)
        self.requests_this_minute = defaultdict(int)
        self.total_requests_this_minute = 0
        
    def log_request(self, ip, endpoint, user_agent='', method='GET'):
        current_time = time.time()
        current_minute = int(current_time // 60)
        
        # Reset counters if new minute
        if current_minute > self.current_minute:
            self.reset_counters()
            
        # Log the request
        request_data = {
            'timestamp': current_time,
            'ip': ip,
            'endpoint': endpoint,
            'user_agent': user_agent,
            'method': method
        }
        request_logs.append(request_data)
        
        # Update counters
        self.requests_this_minute[ip] += 1
        self.total_requests_this_minute += 1
        ip_requests[ip].append(current_time)
        
        # Check for DoS (single IP)
        if self.requests_this_minute[ip] > SECURITY_CONFIG['dos_threshold']:
            self.handle_dos_attack(ip, self.requests_this_minute[ip])
            
        # Check for DDoS (total traffic)
        if self.total_requests_this_minute > SECURITY_CONFIG['ddos_threshold']:
            self.handle_ddos_attack(self.total_requests_this_minute)
            
        # Check for suspicious patterns
        self.check_suspicious_patterns(ip, endpoint, user_agent)
        
    def handle_dos_attack(self, ip, request_count):
        blocked_ips.add(ip)
        attack_info = {
            'type': 'DoS',
            'source_ip': ip,
            'request_count': request_count,
            'timestamp': datetime.now().isoformat(),
            'mitigation': f'IP {ip} blocked'
        }
        attack_logs.append(attack_info)
        security_alerts.append(f"DoS attack detected from {ip} - {request_count} requests/minute")
        
    def handle_ddos_attack(self, total_requests):
        attack_info = {
            'type': 'DDoS',
            'total_requests': total_requests,
            'timestamp': datetime.now().isoformat(),
            'mitigation': 'Enhanced rate limiting activated'
        }
        attack_logs.append(attack_info)
        security_alerts.append(f"DDoS attack detected - {total_requests} total requests/minute")
        
    def check_suspicious_patterns(self, ip, endpoint, user_agent):
        suspicious_score = 0
        
        # Check for suspicious keywords in endpoint
        for pattern in SECURITY_CONFIG['suspicious_patterns']:
            if pattern.lower() in endpoint.lower():
                suspicious_score += 1
                
        # Check for suspicious user agents
        if 'bot' in user_agent.lower() or len(user_agent) < 10:
            suspicious_score += 1
            
        if suspicious_score > 1:
            security_alerts.append(f"Suspicious activity from {ip}: {endpoint}")

security_monitor = SecurityMonitor()

def generate_captcha():
    a, b = random.randint(1, 9), random.randint(1, 9)
    session['captcha_answer'] = str(a + b)
    return f"{a} + {b}"

def is_ip_blocked(ip):
    return ip in blocked_ips

def check_account_locked(username):
    if username in locked_accounts:
        if time.time() < locked_accounts[username]:
            return True
        else:
            del locked_accounts[username]
            failed_attempts[username] = 0
    return False

@app.before_request
def before_request():
    client_ip = get_remote_address()
    
    # Block known malicious IPs
    if is_ip_blocked(client_ip):
        return "Access denied - IP blocked due to suspicious activity", 403
        
    # Log all requests for security monitoring
    security_monitor.log_request(
        ip=client_ip,
        endpoint=request.endpoint or request.path,
        user_agent=request.headers.get('User-Agent', ''),
        method=request.method
    )

@app.route('/', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        captcha_response = request.form['captcha']

        # Check if account is locked
        if check_account_locked(username):
            flash(f"Account locked. Try again later.")
            # Show the same captcha again—do not call generate_captcha here!
            captcha_q = session.get('captcha_q', '???')
            return render_template('login.html', captcha_q=captcha_q)

        # Validate credentials and captcha
        correct_captcha = session.get('captcha_answer')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            if captcha_response == correct_captcha:
                session['username'] = user.username
                session['role'] = user.role
                failed_attempts[username] = 0
                return redirect(url_for('dashboard'))
            else:
                flash("CAPTCHA verification failed.")
        else:
            failed_attempts[username] += 1
            if failed_attempts[username] >= SECURITY_CONFIG['max_failed_attempts']:
                locked_accounts[username] = time.time() + SECURITY_CONFIG['lockout_duration']
                security_alerts.append(f"Account {username} locked due to repeated failed attempts")
            flash("Incorrect username or password.")

        # Show the same captcha again—do not call generate_captcha here!
        captcha_q = session.get('captcha_q', '???')
        return render_template('login.html', captcha_q=captcha_q)

    # Only generate new CAPTCHA on GET
    captcha_q = generate_captcha()
    session['captcha_q'] = captcha_q
    return render_template('login.html', captcha_q=captcha_q)

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user_role = user_roles.get(session['username'], 'user')
    stats = None
    
    if user_role in ['admin', 'security_admin']:
        stats = {
            'total_requests': len(request_logs),
            'blocked_ips': len(blocked_ips),
            'active_attacks': len([a for a in attack_logs if 
                                datetime.fromisoformat(a['timestamp']) > 
                                datetime.now() - timedelta(hours=1)]),
            'security_alerts': len(security_alerts)
        }
    
    return render_template('dashboard.html', 
                         username=session['username'], 
                         role=user_role,
                         stats=stats)

@app.route('/request_service', methods=['POST'])
@limiter.limit("5 per minute")
def request_service():
    if 'username' not in session:
        return "User not logged in.", 401
    
    client_ip = get_remote_address()
    
    # Additional service-specific rate limiting
    service_requests = [r for r in request_logs if 
                       r.get('event') == 'service_request' and 
                       r.get('ip') == client_ip and 
                       time.time() - r.get('timestamp', 0) < 60]
    
    if len(service_requests) > 3:
        security_alerts.append(f"Rate limit exceeded for service requests from {client_ip}")
        return "Rate limit exceeded. Please wait before making another request.", 429
    
    request_logs.append({
        'timestamp': time.time(),
        'event': 'service_request',
        'username': session['username'],
        'ip': client_ip
    })
    
    return "Service request processed and logged!"

@app.route('/security_dashboard')
def security_dashboard():
    if 'username' not in session or user_roles.get(session['username']) not in ['admin', 'security_admin']:
        return "Not authorized", 403
    
    recent_attacks = [a for a in attack_logs if 
                     datetime.fromisoformat(a['timestamp']) > 
                     datetime.now() - timedelta(hours=24)]
    
    return render_template('security_dashboard.html', 
                         attacks=recent_attacks,
                         blocked_ips=list(blocked_ips),
                         alerts=security_alerts[-50:])

@app.route('/view_logs')
def view_logs():
    if 'username' not in session or user_roles.get(session['username']) not in ['admin', 'security_admin']:
        return "Not authorized", 403
    
    # Filter logs for display
    recent_logs = list(request_logs)[-100:]  # Last 100 entries
    
    return render_template('logs.html', logs=recent_logs, attacks=attack_logs)

@app.route('/mitigation', methods=['POST'])
def mitigation():
    if 'username' not in session or user_roles.get(session['username']) not in ['admin', 'security_admin']:
        return "Not authorized", 403
    
    action_type = request.form.get('action_type', '')
    target = request.form.get('target', '')
    
    try:
        if action_type == 'block_ip' and target:
            blocked_ips.add(target)
            mitigation_log = f"IP {target} blocked by {session['username']}"
            
        elif action_type == 'unblock_ip' and target:
            blocked_ips.discard(target)
            mitigation_log = f"IP {target} unblocked by {session['username']}"
            
        elif action_type == 'clear_alerts':
            security_alerts.clear()
            mitigation_log = f"Security alerts cleared by {session['username']}"
            
        elif action_type == 'reset_counters':
            security_monitor.reset_counters()
            mitigation_log = f"Security counters reset by {session['username']}"
            
        else:
            return "Invalid mitigation action", 400
            
        request_logs.append({
            'timestamp': time.time(),
            'event': 'mitigation_action',
            'username': session['username'],
            'action': mitigation_log
        })
        
        return f"Mitigation action completed: {mitigation_log}"
        
    except Exception as e:
        return f"Action failed due to system error: {str(e)}", 500

@app.route('/attack_simulation', methods=['POST'])
def attack_simulation():
    if 'username' not in session or user_roles.get(session['username']) != 'security_admin':
        return "Not authorized", 403
    
    attack_type = request.form.get('attack_type', '')
    
    if attack_type == 'dos_simulation':
        # Simulate DoS attack for testing
        fake_ip = f"192.168.1.{random.randint(100, 200)}"
        for _ in range(150):  # Exceed DoS threshold
            security_monitor.log_request(fake_ip, '/test_endpoint', 'TestBot/1.0')
        
        return f"DoS attack simulation completed from {fake_ip}"
        
    elif attack_type == 'ddos_simulation':
        # Simulate DDoS attack for testing
        for i in range(1200):  # Exceed DDoS threshold
            fake_ip = f"10.0.{random.randint(1, 10)}.{random.randint(1, 255)}"
            security_monitor.log_request(fake_ip, '/test_endpoint', 'TestBot/1.0')
        
        return "DDoS attack simulation completed"
        
    return "Invalid simulation type", 400

@app.route('/api/security_stats')
def security_stats():
    if 'username' not in session or user_roles.get(session['username']) not in ['admin', 'security_admin']:
        return "Not authorized", 403
    
    stats = {
        'total_requests': len(request_logs),
        'blocked_ips_count': len(blocked_ips),
        'attack_count': len(attack_logs),
        'alerts_count': len(security_alerts),
        'recent_attacks': attack_logs[-10:] if attack_logs else []
    }
    
    return jsonify(stats)

@app.route('/send_notification', methods=['POST'])
def send_notification():
    if 'username' not in session or user_roles.get(session['username']) not in ['admin', 'security_admin']:
        return "Not authorized", 403
    
    recipient = request.form['recipient']
    message = request.form['message']
    
    if '@' not in recipient:
        return "Recipient address not valid.", 400
    
    try:
        # In production, implement actual SMTP
        notification_log = f"Security notification sent to {recipient}: {message}"
        request_logs.append({
            'timestamp': time.time(),
            'event': 'notification_sent',
            'username': session['username'],
            'details': notification_log
        })
        return "Security notification sent!"
        
    except Exception as e:
        return f"Email delivery failed: {str(e)}", 500

@app.route('/logout')
def logout():
    if 'username' in session:
        request_logs.append({
            'timestamp': time.time(),
            'event': 'logout',
            'username': session['username'],
            'ip': get_remote_address()
        })
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Add users if your table is empty or for initial testing (don't repeat this, or guard it with if not User.query.first())
        if not User.query.filter_by(username="user1").first():
            db.session.add(User(username="user1", password_hash=generate_password_hash("pass1"), role="user"))
            db.session.add(User(username="admin", password_hash=generate_password_hash("adminpass"), role="admin"))
            db.session.add(User(username="security_admin", password_hash=generate_password_hash("secpass123"), role="security_admin"))
            db.session.commit()

    print("Starting Security-Enhanced Web Application...")
    print("Default accounts:")
    print("- User: user1/pass1")
    print("- Admin: admin/adminpass") 
    print("- Security Admin: security_admin/secpass123")
    app.run(debug=False, host='0.0.0.0', port=5000)
