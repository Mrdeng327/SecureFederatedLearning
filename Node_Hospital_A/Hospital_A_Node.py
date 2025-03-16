import hashlib
import time
import json
import os
import ssl

import requests
import rsa
from flask import Flask, request, jsonify

app = Flask(__name__)

# IPFS API 地址
IPFS_API = "http://127.0.0.1:5001/api/v0/add"
BLOCKCHAIN_A = "hospital_A_blockchain.json"

# 读取医院 A 的公钥（用于验证签名）
with open("../Local_Hospital_A/hospital_A_public.pem", "rb") as pub_file:
    pubkey = rsa.PublicKey.load_pkcs1(pub_file.read())


def save_to_ipfs_A(hospital_id, round_num, encrypted_weights, encrypted_bias, timestamp, signature):
    """直接上传医院 A 的加密梯度到 IPFS，而不存本地文件"""

    signature_str = signature.hex()  # 转换为十六进制字符串

    # 直接创建 JSON 数据
    ipfs_data = {
        "hospital_id": hospital_id,
        "round_num": round_num,
        "encrypted_weights": encrypted_weights,
        "encrypted_bias": encrypted_bias,
        "timestamp": timestamp,
        "signature": signature_str
    }

    try:
        # 直接上传 JSON 数据
        files = {
            "file": ("hospital_A_data.json", json.dumps(ipfs_data), "application/json")
        }
        response = requests.post(IPFS_API , files=files)

        # 解析 IPFS 响应
        if response.status_code == 200:
            ipfs_hash = response.json()["Hash"]
            return f"ipfs://{ipfs_hash}"
        else:
            raise Exception(f"IPFS 上传失败: {response.text}")

    except Exception as e:
        print(f"上传到 IPFS 失败: {e}")
        return None

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

    # 存储到 IPFS

    ipfs_hash = save_to_ipfs_A(hospital_id, round_num, encrypted_weights, encrypted_bias, timestamp, signature)



    # 记录到区块链
    blockchain_status = record_to_blockchain_A(hospital_id, round_num, hash_weights, hash_bias, timestamp, signature)

    return jsonify({
        "status": "success",
        "ipfs_hash": ipfs_hash,
        "blockchain_status": blockchain_status
    })

if __name__ == '__main__':
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain("cert.pem", "key.pem")
    app.run(host='0.0.0.0', port=5004, ssl_context=context)  # 启动 HTTPS
