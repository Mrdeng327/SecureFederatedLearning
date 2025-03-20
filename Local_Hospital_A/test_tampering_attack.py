import requests
import json
import numpy as np
import time
import rsa
import hashlib

# Configuration
NODE_URL = "https://127.0.0.1:5004/upload"  # Hospital node endpoint
EXCHANGE_URL = "https://127.0.0.1:5003/get_otm"  # Mask exchange with Hospital B
HOSPITAL_ID = "Hospital_A"
ROUND_NUM = 1

# Load RSA Private Key
with open("hospital_A_private.pem", "rb") as priv_file:
    privkey = rsa.PrivateKey.load_pkcs1(priv_file.read())

# Load Gradient Data
grad_weights = np.load("grad_weights.npy")  # Weight gradient
grad_bias = np.load("grad_bias.npy")  # Bias gradient

# Fetch Mask from Hospital B
response = requests.get(EXCHANGE_URL, verify=False)
received_data = response.json()
received_mask_weights = np.array(received_data["mask_weights"])
received_mask_bias = float(received_data["mask_bias"])

# Normal Encryption Process
mask_weights = np.random.rand(*grad_weights.shape)  # Generate local mask for weights
mask_bias = np.random.rand()  # Generate local mask for bias

# Apply one-time mask encryption
encrypted_weights = grad_weights + mask_weights - received_mask_weights
encrypted_bias = float(grad_bias) + float(mask_bias) - received_mask_bias


# Compute SHA-256 Hash
def compute_hash(data):
    """Compute SHA-256 hash of the given data."""
    return hashlib.sha256(data.tobytes()).hexdigest()


# Correct hash values (before tampering)
hash_weights = compute_hash(encrypted_weights)
hash_bias = compute_hash(np.array([encrypted_bias]))


# Generate RSA Signature (before tampering)
def sign_data(private_key, hospital_id, round_num, hash_weights, hash_bias, timestamp):
    """Sign the gradient data using RSA."""
    data = json.dumps({
        "hospital_id": hospital_id,
        "round_num": round_num,
        "hash_weights": hash_weights,
        "hash_bias": hash_bias,
        "timestamp": timestamp
    }, sort_keys=True).encode("utf-8")

    signature = rsa.sign(data, private_key, "SHA-256")
    return signature.hex()


# Generate timestamp
timestamp = int(time.time())

# Sign the original hash (before tampering)
signature = sign_data(privkey, HOSPITAL_ID, ROUND_NUM, hash_weights, hash_bias, timestamp)

# Create the Original Payload
original_payload = {
    "hospital_id": HOSPITAL_ID,
    "round_num": ROUND_NUM,
    "encrypted_weights": encrypted_weights.tolist(),
    "encrypted_bias": encrypted_bias,
    "hash_weights": hash_weights,
    "hash_bias": hash_bias,
    "timestamp": timestamp,
    "signature": signature  # Correct signature
}

print("\n Original payload generated...")


# Tamper with the Data
print("\n Tampering with the data...")
tampered_weights = encrypted_weights + np.random.rand(*encrypted_weights.shape) * 0.1  # Modify weight gradient
tampered_bias = encrypted_bias + 0.5  # Modify bias gradient

# Recalculate tampered hash values
tampered_hash_weights = compute_hash(tampered_weights)
tampered_hash_bias = compute_hash(np.array([tampered_bias]))

# Create the Tampered Payload (with original signature)
tampered_payload = {
    "hospital_id": HOSPITAL_ID,
    "round_num": ROUND_NUM,
    "encrypted_weights": tampered_weights.tolist(),
    "encrypted_bias": tampered_bias,
    "hash_weights": tampered_hash_weights,  # Tampered hash
    "hash_bias": tampered_hash_bias,  # Tampered hash
    "timestamp": timestamp,
    "signature": signature  # Original signature (unchanged)
}

print("\n[+] Tampered payload generated...")


# Send Tampered Data
try:
    print("\n Sending tampered data to the hospital node...")
    response = requests.post(NODE_URL, json=tampered_payload, verify=False)

    print(f"\n Response Status Code: {response.status_code}")

    if response.status_code == 400:
        print(" Tampering detected: Signature verification failed. Data rejected!")
    else:
        print(" Tampering not detected: System is vulnerable!")

except Exception as e:
    print(f"[!] Error occurred: {e}")
