import requests
import json

BASE_URL = "http://localhost:5000"

# 1. Login to get token
login_data = {"email": "admin@example.com", "password": "admin"}
try:
    resp = requests.post(f"{BASE_URL}/api/login/", json=login_data)
    token = resp.json().get("token")
    if not token:
        print("Login failed, no token")
        exit(1)
except Exception as e:
    print(f"Login error: {e}")
    exit(1)

headers = {"Authorization": f"Token {token}", "Content-Type": "application/json"}

# 2. Need a user ID to update. Let's create one first or use a known one.
# Re-using the detailed creation from previous test to ensure existence
user_data = {
    "email": "update_test_user@example.com",
    "password": "password123",
    "first_name": "Update",
    "paternal_surname": "Test",
    "role": "STUDENT",
    "ci_number": "88990011"
}
try:
    # Try create (might fail if exists, that's fine, we try to find it then)
    c_resp = requests.post(f"{BASE_URL}/api/manage-users/", json=user_data, headers=headers)
    if c_resp.status_code == 201:
        user_id = c_resp.json().get('id')
    else:
        # If already exists, maybe we can search or assuming ID 4 (from user report) implies some users exist.
        # Let's try to get the user list to find this user
        l_resp = requests.get(f"{BASE_URL}/api/manage-users/?search=88990011", headers=headers)
        results = l_resp.json().get('results', [])
        if results:
            user_id = results[0]['id']
        else:
            print("Could not find user to update")
            exit(1)
except Exception as e:
    print(f"Setup error: {e}")
    exit(1)

print(f"Target User ID: {user_id}")

# 3. Simulate Frontend PUT Request with empty password
# UserDialog sends all values from Formik.
put_data = {
    "email": "update_test_user@example.com",
    "first_name": "Update Modified",
    "paternal_surname": "Test",
    "maternal_surname": "",
    "ci_number": "88990011",
    "password": "",  # THIS IS LIKELY THE ISSUE
    "role": "STUDENT"
}

print("Attempting PUT with empty password...")
resp = requests.put(f"{BASE_URL}/api/manage-users/{user_id}/", json=put_data, headers=headers)
print(f"Status: {resp.status_code}")
print("Body:", resp.text)
