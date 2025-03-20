import requests
import json
import numpy as np
import time
import rsa
import hashlib

# --- Configuration ---
NODE_URL = "http://127.0.0.1:5004/upload"  # Using HTTP instead of HTTPS
HOSPITAL_ID = "Hospital_A"
ROUND_NUM = 1

# --- Load Keys ---
with open("hospital_A_private.pem", "rb") as priv_file:
    privkey = rsa.PrivateKey.load_pkcs1(priv_file.read())

# --- Generate Fake Gradient Data ---
fake_weights = np.random.rand(3, 3)  # Simulating random gradient weights
fake_bias = np.random.rand()  # Simulating random gradient bias

# --- Compute Hashes ---
def compute_hash(data):
    """Compute SHA-256 hash"""
    return hashlib.sha256(data.tobytes()).hexdigest()

# Calculate hashes
hash_weights = compute_hash(fake_weights)
hash_bias = compute_hash(np.array([fake_bias]))

# --- Generate RSA Signature ---
def sign_data(private_key, hospital_id, round_num, hash_weights, hash_bias, timestamp):
    """Generate signature"""
    data = json.dumps({
        "hospital_id": hospital_id,
        "round_num": round_num,
        "hash_weights": hash_weights,
        "hash_bias": hash_bias,
        "timestamp": timestamp
    }, sort_keys=True).encode("utf-8")

    signature = rsa.sign(data, private_key, "SHA-256")
    return signature.hex()

timestamp = int(time.time())
signature = sign_data(privkey, HOSPITAL_ID, ROUND_NUM, hash_weights, hash_bias, timestamp)

# --- Prepare Data for Upload ---
payload = {
    "hospital_id": HOSPITAL_ID,
    "round_num": ROUND_NUM,
    "encrypted_weights": fake_weights.tolist(),
    "encrypted_bias": fake_bias,
    "hash_weights": hash_weights,
    "hash_bias": hash_bias,
    "timestamp": timestamp,
    "signature": signature
}

# --- Make HTTP Request (Without TLS) ---
try:
    print("\n[+] Sending gradient data without TLS...")

    # Using HTTP instead of HTTPS to simulate unencrypted communication
    response = requests.post(NODE_URL, json=payload, timeout=10)

    print(f"Response: {response.status_code}")
    print(f"Response Body: {response.text}")

except requests.exceptions.ConnectionError as e:
    if "10054" in str(e):  # Checking for error code 10054
        print(" [❗] Error: ('Connection aborted.', ConnectionResetError(10054, 'The remote host forcibly closed an existing connection.', None, 10054, None))\nThe server enforces the use of TLS and rejects unencrypted HTTP communication.")
