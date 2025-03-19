import hashlib
import time
import json
import os
import ssl

import requests
import rsa
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)

limiter = Limiter(key_func=get_remote_address)
limiter.init_app(app)

# Read the public key of Hospital A (for signature verification)
LOCAL_IPFS_API = "http://127.0.0.1:5001/api/v0/add"
PINATA_API_URL = "https://api.pinata.cloud/pinning/pinFileToIPFS"  # Pinata IPFS API
PINATA_API_KEY = "9ff40d2d04c6f4758d7f"  # Pinata API key
PINATA_SECRET_API_KEY = "59dabf5eed8aeb8cda608e218ef7f1a7e9c684d89f2bafc3efea2651047686d8"  # Pinata API key

BLOCKCHAIN_A = "hospital_A_blockchain.json"

with open("../Local_Hospital_A/hospital_A_public.pem", "rb") as pub_file:
    pubkey = rsa.PublicKey.load_pkcs1(pub_file.read())


def save_to_ipfs_A(hospital_id, round_num, encrypted_weights, encrypted_bias, timestamp, signature):
    """Upload the encrypted gradient of Hospital A directly to IPFS without storing local files"""

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

        files = {"file": ("hospital_A_data.json", json.dumps(ipfs_data), "application/json")}
        response = requests.post(LOCAL_IPFS_API, files=files)

        # Parse the IPFS response
        if response.status_code == 200:
            local_ipfs_hash = response.json()["Hash"]
            print(f" Local IPFS upload successful: {local_ipfs_hash}")
        else:
            raise Exception(f"Local IPFS upload failed: {response.text}")

        # Upload to Pinata
        headers = {
            "pinata_api_key": PINATA_API_KEY,
            "pinata_secret_api_key": PINATA_SECRET_API_KEY
        }
        pinata_response = requests.post(PINATA_API_URL, files=files, headers=headers)

        if pinata_response.status_code == 200:
            pinata_ipfs_hash = pinata_response.json()["IpfsHash"]
            print(f" Pinata IPFS upload successful: {pinata_ipfs_hash}")
            return {
                "local_ipfs": f"ipfs://{local_ipfs_hash}",
                "pinata": f"https://gateway.pinata.cloud/ipfs/{pinata_ipfs_hash}"
            }
        else:
            raise Exception(f"Pinata upload failed: {pinata_response.text}")

    except Exception as e:
        print(f" IPFS upload failed: {e}")
        return None


def record_to_blockchain_A(hospital_id, round_num, hash_weights, hash_bias, timestamp, signature):
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

    # Read existing data and append new data
    if os.path.exists(BLOCKCHAIN_A):
        with open(BLOCKCHAIN_A, "r") as file:
            try:
                existing_data = json.load(file)
            except json.JSONDecodeError:
                existing_data = []
    else:
        existing_data = []

    existing_data.append(blockchain_data)

    with open(BLOCKCHAIN_A, "w") as file:
        json.dump(existing_data, file, indent=4)

    return "Blockchain record success"


@app.route('/upload', methods=['POST'])
@limiter.limit("5 per minute")
def upload_model_A():
    """Receive model updates from Hospital A"""
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

    # Upload data to IPFS
    ipfs_hash = save_to_ipfs_A(hospital_id, round_num, encrypted_weights, encrypted_bias, timestamp, signature)

    # Record to the blockchain
    blockchain_status = record_to_blockchain_A(hospital_id, round_num, hash_weights, hash_bias, timestamp, signature)

    return jsonify({
        "status": "success",
        "ipfs_hash": ipfs_hash,
        "blockchain_status": blockchain_status,
    })


if __name__ == '__main__':
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain("cert.pem", "key.pem")
    app.run(host='0.0.0.0', port=5004, ssl_context=context)  #
