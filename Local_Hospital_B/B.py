import hashlib
import time
import json
import rsa
import requests
import ssl
import numpy as np
from flask import Flask, jsonify, request

app = Flask(__name__)
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True

HOSPITAL_ID = "Hospital_B"
EXCHANGE_URL = "https://127.0.0.1:5002/get_otm"  # Switching mask (hospital A)
NODE_URL = "https://127.0.0.1:5005/upload"  # Upload Hospital Node B
ROUND_NUM = 1  # Rounds start at 1

# Read local gradient
grad_weights = np.load("grad_weights2_padded.npy")
grad_bias = np.load("grad_bias2.npy")

# Make sure grad_bias is a NumPy array.
if isinstance(grad_bias, (float, int)):
    grad_bias = np.array([grad_bias])

# Generate Local Mask
mask_weights = np.random.rand(*grad_weights.shape)  # 保持数组形状
mask_bias = np.random.rand()  # 生成单个随机数

# Read private key (for signing)
with open("hospital_B_private.pem", "rb") as priv_file:
    privkey = rsa.PrivateKey.load_pkcs1(priv_file.read())

# Compute the SHA-256 hash
def compute_hash(data):
    return hashlib.sha256(data.tobytes()).hexdigest()

# Generate Signature
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




# API: Get the mask of the other hospital A
@app.route("/get_otm", methods=["GET"])
def get_otm():
    return jsonify({
        "mask_weights": mask_weights.tolist(),
        "mask_bias": float(mask_bias)
    })

# API: Process gradient encryption & upload to hospital node B
@app.route("/upload_encrypted_gradients", methods=["POST"])
def upload_encrypted_gradients():
    global ROUND_NUM

    try:
        # Request hospital A for mask
        response = requests.get(EXCHANGE_URL, verify=False)
        received_data = response.json()
        received_mask_weights = np.array(received_data["mask_weights"])
        received_mask_bias = float(received_data["mask_bias"])

        # Calculate the encryption gradient
        encrypted_weights = grad_weights + mask_weights - received_mask_weights
        encrypted_bias = float(grad_bias) + float(mask_bias) - received_mask_bias

        # Calculate the hash
        hash_weights = compute_hash(encrypted_weights)
        hash_bias = compute_hash(np.array([encrypted_bias]))  # Need NumPy arrays to calculate hashes
        timestamp = int(time.time())

        # Signature generation
        signature = sign_data(privkey, HOSPITAL_ID, ROUND_NUM, hash_weights, hash_bias, timestamp)

        # Upload data to hospital node B
        payload = {
            "hospital_id": HOSPITAL_ID,
            "round_num": ROUND_NUM,
            "encrypted_weights": encrypted_weights.tolist(),
            "encrypted_bias": encrypted_bias,  # 直接用 float
            "hash_weights": hash_weights,
            "hash_bias": hash_bias,
            "timestamp": timestamp,
            "signature": signature
        }
        response = requests.post(NODE_URL, json=payload, verify=False)

        # Round +1 to ensure that the next one is a new round
        ROUND_NUM += 1

        return jsonify(response.json())

    except Exception as e:
        return jsonify({"error": str(e)}), 500




if __name__ == "__main__":
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain("cert.pem", "key.pem")
    app.run(host="0.0.0.0", port=5003, ssl_context=context)
