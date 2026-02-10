
import requests
import sys

# Try to register a user to get a token, or login
BASE_URL = "http://localhost:5000/api"

def get_token():
    import random
    import string
    rand_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    email = f"debug_{rand_suffix}@example.com"
    password = "debug_password"
    
    # Register
    print(f"Registering {email}...")
    try:
        resp = requests.post(f"{BASE_URL}/register/", data={
            "email": email, 
            "password": password, 
            "first_name": "Debug", 
            "paternal_surname": "User",
            "role": "ADMIN"
        })
        if resp.status_code == 201:
             # Some setups return token on register
             if 'token' in resp.json():
                 return resp.json()['token']
    except Exception as e:
        print(f"Registration exception: {e}")

    # Login
    resp = requests.post(f"{BASE_URL}/login/", data={"email": email, "password": password})
    if resp.status_code == 200:
        return resp.json().get('token')
    else:
        print("Login failed:", resp.text)
        return None

token = get_token()
if not token:
    # Try one more, maybe the admin created earlier
    try:
        resp = requests.post(f"{BASE_URL}/login/", data={"email": "test@example.com", "password": "password"})
        if resp.status_code == 200:
            token = resp.json().get('token')
    except:
        pass

if not token:
    print("Could not get token. Aborting.")
    sys.exit(1)

headers = {"Authorization": f"Token {token}"}
data = {"name": "Live Test Program"}

print(f"Sending POST to {BASE_URL}/programs/ ...")
resp = requests.post(f"{BASE_URL}/programs/", json=data, headers=headers)

print(f"Status Code: {resp.status_code}")

if resp.status_code == 500:
    print("Got 500 Error.")
    # Try to extract traceback from HTML
    if "<html" in resp.text:
        # It's the Django debug page
        from bs4 import BeautifulSoup
        try:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # The traceback is usually in a div with class 'context' or similar, 
            # or we can just print text content to find "Traceback"
            
            # Simplified approach: print lines containing "File"
            print("\n--- EXTRACTED TRACEBACK ---")
            lines = resp.text.split('\n')
            printing = False
            for line in lines:
                if "Traceback" in line:
                    printing = True
                if printing:
                    # Remove html tags partially
                    import re
                    clean_line = re.sub(r'<[^>]+>', '', line).strip()
                    if clean_line:
                        print(clean_line)
                    if "The above exception was the direct cause" in line:
                         break
        except ImportError:
            print("BeautifulSoup not installed, printing text snippet:")
            print(resp.text[:2000])
    else:
        print("Response JSON (if any):", resp.text)
else:
    print("Success:", resp.text)
