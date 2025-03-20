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

from web3 import Web3, HTTPProvider

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import base64

import numpy as np

app = Flask(__name__)

limiter = Limiter(key_func=get_remote_address)
limiter.init_app(app)

# Read the public key of Hospital A (for signature verification)
LOCAL_IPFS_API = "http://127.0.0.1:5001/api/v0/add"
IPFS_RETRIEVAL = "http://127.0.0.1:8080/ipfs/"
PINATA_API_URL = "https://api.pinata.cloud/pinning/pinFileToIPFS"  # Pinata IPFS API
PINATA_API_KEY = "9ff40d2d04c6f4758d7f"  # Pinata API key
PINATA_SECRET_API_KEY = "59dabf5eed8aeb8cda608e218ef7f1a7e9c684d89f2bafc3efea2651047686d8"  # Pinata API key


with open("../Local_Hospital_A/hospital_A_public.pem", "rb") as pub_file:
    pubkey = rsa.PublicKey.load_pkcs1(pub_file.read())

with open("hospital_A_private.pem", "rb") as priv_file:
    privkey = rsa.PrivateKey.load_pkcs1(priv_file.read())

# Connect to web3
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:7545'))
CONTRACT_ADDRESS = "0x16d8FD14D7521202161089276450b37b5cE3F548"
with open("../../blockchain/build/contracts/IncentiveScheme.json", "r") as f:
    contract_json = json.load(f)

contract_abi = contract_json["abi"]
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)
HOSPITAL_A_ADDRESS = w3.eth.accounts[2]
PRIVATE_KEY = "0x91d55480f962cd4081a4037ca263bd8ac4ce7022f166f36ba8376ab96cdb9b75"


def save_to_ipfs_A(hospital_id, round_num, masked_weights, masked_bias, acc_improvement, timestamp, signature):
    signature_str = signature.hex()  # Convert to hexadecimal string

    # Create JSON data directly
    ipfs_data = {
        "hospital_id": hospital_id,
        "round_num": round_num,
        "masked_weights": masked_weights,
        "masked_bias": masked_bias,
        "acc_improvement": acc_improvement,
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
            return local_ipfs_hash
        else:
            raise Exception(f"Local IPFS upload failed: {response.text}")

        # # Upload to Pinata
        # headers = {
        #     "pinata_api_key": PINATA_API_KEY,
        #     "pinata_secret_api_key": PINATA_SECRET_API_KEY
        # }
        # pinata_response = requests.post(PINATA_API_URL, files=files, headers=headers)

        # if pinata_response.status_code == 200:
        #     pinata_ipfs_hash = pinata_response.json()["IpfsHash"]
        #     print(f" Pinata IPFS upload successful: {pinata_ipfs_hash}")
        #     return {
        #         "local_ipfs": f"ipfs://{local_ipfs_hash}",
        #         "pinata": f"https://gateway.pinata.cloud/ipfs/{pinata_ipfs_hash}"
        #     }
        # else:
        #     raise Exception(f"Pinata upload failed: {pinata_response.text}")

    except Exception as e:
        print(f" IPFS upload failed: {e}")
        return None


def record_to_blockchain_A(ipfs_cid):
    """Upload the IPFS CID to the smart contract"""
    stake_wei = Web3.to_wei(0.1, "ether")

    tx = contract.functions.submitGradientUpdate(ipfs_cid).build_transaction({
        "from": HOSPITAL_A_ADDRESS,
        "value": stake_wei,
        "nonce": w3.eth.get_transaction_count(HOSPITAL_A_ADDRESS)
    })

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(receipt.transactionHash.hex())
    return receipt


@app.route('/upload', methods=['POST'])
@limiter.limit("5 per minute")
def upload_model_A():
    """Receive model updates from Hospital A"""
    data = request.json

    # extract parameter
    hospital_id = data.get("hospital_id")
    round_num = data.get("round_num")
    masked_weights = data.get("masked_weights")
    masked_bias = data.get("masked_bias")
    acc_improvement = data.get("acc_improvement")
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
    ipfs_cid = save_to_ipfs_A(hospital_id, round_num, masked_weights, masked_bias, acc_improvement, timestamp, signature)

    receipt = None
    if ipfs_cid:
        receipt = record_to_blockchain_A(ipfs_cid)

    return jsonify({
        "status": "success",
        "ipfs_cid": ipfs_cid,
        "contractTx": receipt.transactionHash.hex() if receipt else None
    })


def retrieve_from_ipfs(cid):
    url = f"{IPFS_RETRIEVAL}{cid}"
    response = requests.get(url)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch data from IPFS for CID: {cid}")
        return None


def decrypt_global_model(encrypted_data):
    encrypted_key = base64.b64decode(encrypted_data["aes_key"])
    decrypted_key = rsa.decrypt(encrypted_key, privkey) 

    nonce = base64.b64decode(encrypted_data["nonce"])
    ciphertext = base64.b64decode(encrypted_data["ciphertext"])
    tag = base64.b64decode(encrypted_data["tag"])

    cipher = AES.new(decrypted_key, AES.MODE_GCM, nonce=nonce)
    decrypted_data = cipher.decrypt_and_verify(ciphertext, tag)

    return json.loads(decrypted_data.decode("utf-8"))


# This testing functionality is for demonstrative purposes only. The hospital would not actually have the others raw gradients.
def test_aggregation(weights, bias):
    A_grad_weights = np.load("../Local_Hospital_A/grad_weights.npy")
    A_grad_bias = np.load("../Local_Hospital_A/grad_bias.npy")

    B_grad_weights = np.load("../Local_Hospital_B/grad_weights2_padded.npy")
    B_grad_bias = np.load("../Local_Hospital_B/grad_bias2.npy")

    raw_aggregated_weights = A_grad_weights + B_grad_weights
    raw_aggregated_bias = A_grad_bias + B_grad_bias

    weights_match = np.allclose(raw_aggregated_weights, weights)
    bias_match = np.isclose(raw_aggregated_bias, bias)

    if weights_match and bias_match:
        print("Test passed: Aggregated weights and biases match the sum of raw gradients.")
        return True
    else:
        print("Test failed: Aggregated weights and biases do not match the sum of raw gradients.")
        if not weights_match:
            print("Weights do not match.")
        if not bias_match:
            print("Biases do not match.")


# Retrieves global sum from ipfs, decrypts it and tests that it is correctly calculated.
# This testing functionality is for demonstrative purposes only. The hospital would not actually have the others raw gradients.
@app.route('/retrieve_global_model', methods=['GET'])
def retrieve_global_model():
    participant_data = contract.functions.getParticipant(HOSPITAL_A_ADDRESS).call()

    if not participant_data[7]: 
        return jsonify({"status": "error", "message": "Not permitted to access global model"}), 403

    global_model_cid = participant_data[8]
    encrypted_global_model = retrieve_from_ipfs(global_model_cid)

    global_model = decrypt_global_model(encrypted_global_model)

    weights = np.array(global_model["weights"])
    bias = np.array(global_model["bias"])

    if test_aggregation(weights, bias):
        np.save("global_weights.npy", weights)
        np.save("global_bias.npy", bias)
        return jsonify(global_model)
    else:
        return "Retrieved global sum does not match correct sum"
    


if __name__ == '__main__':
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain("cert.pem", "key.pem")
    app.run(host='0.0.0.0', port=5004, ssl_context=context) 
