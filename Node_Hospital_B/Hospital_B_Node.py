import hashlib
import time
import json
import os
import ssl

import requests
import rsa
from flask import Flask, request, jsonify

app = Flask(__name__)

# IPFS API address
IPFS_API = "http://127.0.0.1:5001/api/v0/add"
BLOCKCHAIN_B = "hospital_B_blockchain.json"

# Read the public key of Hospital A (for signature verification)
with open("../Local_Hospital_B/hospital_B_public.pem", "rb") as pub_file:
    pubkey = rsa.PublicKey.load_pkcs1(pub_file.read())


def save_to_ipfs_B(hospital_id, round_num, encrypted_weights, encrypted_bias, timestamp, signature):
    """Upload the encrypted gradient of Hospital B directly to IPFS without storing local files"""

    signature_str = signature.hex()  # Convert to hexadecimal string

    # Create JSON data directly
    ipfs_data = {
        "hospital_id": hospital_id,
        "round_num": round_num,
        "encrypted_weights": encrypted_weights,
        "encrypted_bias": encrypted_bias,
        "timestamp": timestamp,
        "signature": signature_str
    }

    try:
        # Directly uploading JSON data
        files = {
            "file": ("hospital_A_data.json", json.dumps(ipfs_data), "application/json")
        }
        response = requests.post(IPFS_API , files=files)

        # Parsing IPFS Responses
        if response.status_code == 200:
            ipfs_hash = response.json()["Hash"]
            return f"ipfs://{ipfs_hash}"
        else:
            raise Exception(f"Local IPFS upload failed: {response.text}")

    except Exception as e:
        print(f"Local IPFS upload failed: {e}")
        return None

def record_to_blockchain_B(hospital_id, round_num, hash_weights, hash_bias, timestamp, signature):
    """Simulate storing hashes to the blockchain"""
    signature_str = signature.hex()  # Convert to hexadecimal string

    blockchain_data = {
        "hospital_id": hospital_id,
        "round_num": round_num,
        "hash_weights": hash_weights,
        "hash_bias": hash_bias,
        "timestamp": timestamp,
        "signature": signature_str
    }

    # 读取已有数据，追加新数据Read existing data and append new data
    if os.path.exists(BLOCKCHAIN_B):
        with open(BLOCKCHAIN_B, "r") as file:
            try:
                existing_data = json.load(file)
            except json.JSONDecodeError:
                existing_data = []
    else:
        existing_data = []

    existing_data.append(blockchain_data)

    with open(BLOCKCHAIN_B, "w") as file:
        json.dump(existing_data, file, indent=4)

    return "Blockchain record success"

@app.route('/upload', methods=['POST'])
def upload_model_B():
    """Receive model updates from Hospital B"""
    data = request.json

    # extract parameter
    hospital_id = data.get("hospital_id")
    round_num = data.get("round_num")
    encrypted_weights = data.get("encrypted_weights")
    encrypted_bias = data.get("encrypted_bias")
    hash_weights = data.get("hash_weights")
    hash_bias = data.get("hash_bias")
    timestamp = data.get("timestamp")
    signature = bytes.fromhex(data.get("signature"))

    # Verify Signature
    payload_str = json.dumps({
        "hospital_id": hospital_id,
        "round_num": round_num,
        "hash_weights": hash_weights,
        "hash_bias": hash_bias,
        "timestamp": timestamp,
    }, sort_keys=True).encode("utf-8")

    try:
        rsa.verify(payload_str, signature, pubkey)
    except rsa.VerificationError:
        return jsonify({"status": "error", "message": "Signature verification failed"}), 400

    # Store to IPFS

    ipfs_hash = save_to_ipfs_B(hospital_id, round_num, encrypted_weights, encrypted_bias, timestamp, signature)



    # Record to the blockchain
    blockchain_status = record_to_blockchain_B(hospital_id, round_num, hash_weights, hash_bias, timestamp, signature)

    return jsonify({
        "status": "success",
        "ipfs_hash": ipfs_hash,
        "blockchain_status": blockchain_status
    })

if __name__ == '__main__':
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain("cert.pem", "key.pem")
    app.run(host='0.0.0.0', port=5005, ssl_context=context)  # 启动 HTTPS
