import hashlib
import time
import json
import os
import ssl
import rsa
from flask import Flask, request, jsonify

app = Flask(__name__)

# 模拟存储路径
IPFS_STORAGE_A = "hospital_A_ipfs_storage.json"
BLOCKCHAIN_A = "hospital_A_blockchain.json"

# 读取医院 A 的公钥（用于验证签名）
with open("../Local_Hospital_A/hospital_A_public.pem", "rb") as pub_file:
    pubkey = rsa.PublicKey.load_pkcs1(pub_file.read())

def save_to_ipfs_A(hospital_id, round_num, encrypted_weights, encrypted_bias, timestamp, signature):
    """模拟存储到 IPFS"""
    signature_str = signature.hex()  # 转换为十六进制字符串

    ipfs_data = {
        "hospital_id": hospital_id,
        "round_num": round_num,
        "encrypted_weights": encrypted_weights,
        "encrypted_bias": encrypted_bias,
        "timestamp": timestamp,
        "signature": signature_str
    }

    # 读取已有数据，追加新数据
    if os.path.exists(IPFS_STORAGE_A):
        with open(IPFS_STORAGE_A, "r") as file:
            try:
                existing_data = json.load(file)
            except json.JSONDecodeError:
                existing_data = []
    else:
        existing_data = []

    existing_data.append(ipfs_data)

    with open(IPFS_STORAGE_A, "w") as file:
        json.dump(existing_data, file, indent=4)

    return f"ipfs://mock_hash_A_{int(time.time())}"

def record_to_blockchain_A(hospital_id, round_num, hash_weights, hash_bias, timestamp, signature):
    """模拟将哈希存储到区块链"""
    signature_str = signature.hex()  # 转换为十六进制字符串

    blockchain_data = {
        "hospital_id": hospital_id,
        "round_num": round_num,
        "hash_weights": hash_weights,
        "hash_bias": hash_bias,
        "timestamp": timestamp,
        "signature": signature_str
    }

    # 读取已有数据，追加新数据
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
def upload_model_A():
    """接收医院 A 发送的模型更新"""
    data = request.json

    # 提取参数
    hospital_id = data.get("hospital_id")
    round_num = data.get("round_num")
    encrypted_weights = data.get("encrypted_weights")
    encrypted_bias = data.get("encrypted_bias")
    hash_weights = data.get("hash_weights")
    hash_bias = data.get("hash_bias")
    timestamp = data.get("timestamp")
    signature = bytes.fromhex(data.get("signature"))

    # 验证签名
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

    # 存储到 IPFS（模拟）
    ipfs_hash = save_to_ipfs_A(hospital_id, round_num, encrypted_weights, encrypted_bias, timestamp, signature)

    # 记录到区块链（模拟）
    blockchain_status = record_to_blockchain_A(hospital_id, round_num, hash_weights, hash_bias, timestamp, signature)

    return jsonify({
        "status": "success",
        "ipfs_hash": ipfs_hash,
        "blockchain_status": blockchain_status
    })

if __name__ == '__main__':
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain("cert.pem", "key.pem")
    app.run(host='0.0.0.0', port=5002, ssl_context=context)  # 启动 HTTPS
