import requests
import json
import numpy as np
import time
import rsa
import hashlib

# --- Configuration ---
NODE_URL = "https://127.0.0.1:5004/upload"
HOSPITAL_ID = "Hospital_A"
ROUND_NUM = 1

# --- Load Keys ---
with open("hospital_A_private.pem", "rb") as priv_file:
    privkey = rsa.PrivateKey.load_pkcs1(priv_file.read())

# --- Generate Fake Data ---
# Fake gradient data
fake_weights = np.random.rand(3, 3)  # Random weights
fake_bias = np.random.rand()


# --- Compute Hashes ---
def compute_hash(data):
    return hashlib.sha256(data.tobytes()).hexdigest()


# Generate valid hash
hash_weights = compute_hash(fake_weights)
hash_bias = compute_hash(np.array([fake_bias]))

# Simulate Unauthorized Access
# Invalid Signature (generated with wrong key)
with open("../Local_Hospital_B/hospital_B_private.pem", "rb") as fake_priv_file:
    fake_privkey = rsa.PrivateKey.load_pkcs1(fake_priv_file.read())

# Generate signature with Hospital B's key
timestamp = int(time.time())


def sign_data(private_key, hospital_id, round_num, hash_weights, hash_bias, timestamp):
    data = json.dumps({
        "hospital_id": hospital_id,
        "round_num": round_num,
        "hash_weights": hash_weights,
        "hash_bias": hash_bias,
        "timestamp": timestamp
    }, sort_keys=True).encode("utf-8")

    signature = rsa.sign(data, private_key, "SHA-256")
    return signature.hex()


# Sign with invalid key
fake_signature = sign_data(fake_privkey, HOSPITAL_ID, ROUND_NUM, hash_weights, hash_bias, timestamp)

# --- Send Unauthorized Request ---
payload = {
    "hospital_id": HOSPITAL_ID,
    "round_num": ROUND_NUM,
    "encrypted_weights": fake_weights.tolist(),
    "encrypted_bias": fake_bias,
    "hash_weights": hash_weights,
    "hash_bias": hash_bias,
    "timestamp": timestamp,
    "signature": fake_signature  # Invalid signature
}

try:
    print("[+] Sending unauthorized request...")
    response = requests.post(NODE_URL, json=payload, verify=False)

    print(f"Response: {response.status_code}, {response.json()}")

    if response.status_code == 400:
        print(" Unauthorized access detected: Signature verification failed.")
    else:
        print(" Unauthorized access succeeded. System is vulnerable.")

except Exception as e:
    print(f"[!] Error: {e}")
