import requests
import json

BASE_URL = "http://localhost:5000"

# 1. Login
login_data = {
    "email": "admin@example.com",
    "password": "admin"
}

print("Logging in...")
try:
    response = requests.post(f"{BASE_URL}/api/login/", json=login_data)
    if response.status_code != 200:
        print(f"Login failed: {response.status_code}")
        print(response.text)
        exit(1)
    
    token = response.json().get("token")
    print("Login successful. Token obtained.")
except Exception as e:
    print(f"Login exception: {e}")
    exit(1)

# 2. Create User
headers = {
    "Authorization": f"Token {token}",
    "Content-Type": "application/json"
}

user_data = {
    "email": "student_api_test@example.com",
    "password": "password123",
    "first_name": "API Test",
    "paternal_surname": "Student",
    "role": "STUDENT",
    "ci_number": "11223344"
}

print("Attempting to create user via API...")
try:
    response = requests.post(f"{BASE_URL}/api/manage-users", json=user_data, headers=headers)
    print(f"Status Code: {response.status_code}")
    print("Response Body:")
    print(response.text)
except Exception as e:
    print(f"Request exception: {e}")
