import hashlib
import time
import json
import rsa
import requests  # 需要 requests 库
import ssl
import numpy as np
from flask import Flask, jsonify

app = Flask(__name__)

# 假设的模型参数
W_B = np.array([0.6, -0.3, 0.8])  # B 的模型参数
M_B = np.random.rand(3)  # B 生成的本地掩码

HOSPITAL_B_NODE_URL = "https://127.0.0.1:5003/upload"

# 读取私钥（用于签名）
with open("hospital_B_private.pem", "rb") as priv_file:
    privkey = rsa.PrivateKey.load_pkcs1(priv_file.read())

@app.route('/get_otm', methods=['GET'])
def get_otm():
    """医院 B 返回自己的掩码 M_B"""
    return jsonify({"otm": M_B.tolist()})

@app.route('/request_otm_from_A', methods=['GET'])
def request_otm_from_A():
    """医院 B 访问医院 A，获取 A 的 OTM，并进行计算"""
    url = "https://127.0.0.1:5000/get_otm"  # 访问医院 A
    response = requests.get(url, verify=False)  # 获取 A 的掩码
    otm_from_A = np.array(response.json()["otm"])

    # 计算加掩码的参数
    W_B_masked = W_B + M_B  # 先加上 B 的掩码
    W_B_final = W_B_masked - otm_from_A  # 再去掉 A 的掩码

    # 计算哈希值
    W_B_final_hash = hashlib.sha256(W_B_final.tobytes()).hexdigest()

    # 发送到医院节点（On-Chain 代理服务器）
    payload = {
        "hospital_id": "B",
        "round": 1,  # 训练轮次（后续可从 ML 代码获取）
        "W_final": W_B_final.tolist(),
        "W_final_hash": W_B_final_hash,
        "timestamp": int(time.time()),  # 当前时间戳（秒级）
    }

    # 用医院 B 的私钥对 payload 进行签名
    payload_str = json.dumps(payload, sort_keys=True).encode("utf-8")  # 规范化 JSON 后签名
    signature = rsa.sign(payload_str, privkey, "SHA-256")  # 生成签名
    payload["signature"] = signature.hex()  # 转成十六进制字符串，方便传输

    response = requests.post(HOSPITAL_B_NODE_URL, json=payload, verify=False)

    return jsonify({
        "W_B_final": W_B_final.tolist(),  # W_B + M_B - M_A
        "W_B_final_hash": W_B_final_hash,  # 哈希值（未来上链）
        "upload_status": response.json()  # 医院节点的返回信息
    })

if __name__ == '__main__':
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('cert.pem', 'key.pem')
    app.run(host='0.0.0.0', port=5001, ssl_context=context)  # 启动 HTTPS
