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

def save_to_ipfs_A(hospital_id, round, W_final, timestamp, signature):
    """模拟存储到 IPFS"""

    # 将 signature 转换为十六进制字符串
    signature_str = signature.hex()

    ipfs_data = {
        "hospital_id": hospital_id,
        "round": round,
        "W_final": W_final,
        "timestamp": timestamp,
        "signature": signature_str  # 使用十六进制字符串替代原来的 bytes
    }
    # 存储数据到本地 JSON 模拟 IPFS 存储
    with open(IPFS_STORAGE_A, "a") as file:
        json.dump(ipfs_data, file)
        file.write("\n")  # 每个 JSON 对象换行，便于读取

    return f"ipfs://mock_hash_A_{int(time.time())}"

def record_to_blockchain_A(hospital_id, round, W_final_hash, timestamp, signature):
    """模拟将哈希存储到区块链"""

    # 将 signature 转换为十六进制字符串
    signature_str = signature.hex()

    blockchain_data = {
        "hospital_id": hospital_id,
        "round": round,
        "W_final_hash": W_final_hash,
        "timestamp": timestamp,
        "signature": signature_str  # 使用十六进制字符串替代原来的 bytes
    }
    # 存储数据到本地 JSON 模拟区块链存储
    with open(BLOCKCHAIN_A, "a") as file:
        json.dump(blockchain_data, file)
        file.write("\n")  # 每个 JSON 对象换行，便于读取
    return "Blockchain record success"

@app.route('/upload', methods=['POST'])
def upload_model_A():
    """接收医院 A 发送的模型更新"""
    data = request.json

    # 提取参数
    hospital_id = data.get("hospital_id")
    W_final = data.get("W_final")
    W_final_hash = data.get("W_final_hash")
    timestamp = data.get("timestamp")
    signature = bytes.fromhex(data.get("signature"))
    round = data.get("round", 1)  # 默认轮次为 1

    # 验证签名
    payload_str = json.dumps({
        "hospital_id": hospital_id,
        "round": round,
        "W_final": W_final,
        "W_final_hash": W_final_hash,
        "timestamp": timestamp,
    }, sort_keys=True).encode("utf-8")

    try:
        rsa.verify(payload_str, signature, pubkey)
    except rsa.VerificationError:
        return jsonify({"status": "error", "message": "Signature verification failed"}), 400

    # 存储到 IPFS（模拟）
    ipfs_hash = save_to_ipfs_A(hospital_id, round, W_final, timestamp, signature)

    # 记录到区块链（模拟）
    blockchain_status = record_to_blockchain_A(hospital_id, round, W_final_hash, timestamp, signature)

    return jsonify({
        "status": "success",
        "ipfs_hash": ipfs_hash,
        "blockchain_status": blockchain_status
    })

if __name__ == '__main__':
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain("cert.pem", "key.pem")
    app.run(host='0.0.0.0', port=5002, ssl_context=context)
