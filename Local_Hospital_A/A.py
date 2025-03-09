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
W_A = np.array([0.7, -0.4, 0.7])  # A 的模型参数
M_A = np.random.rand(3)  # A 生成的本地掩码

HOSPITAL_A_NODE_URL = "https://127.0.0.1:5002/upload"

# 读取私钥（用于签名）
with open("hospital_A_private.pem", "rb") as priv_file:
    privkey = rsa.PrivateKey.load_pkcs1(priv_file.read())

@app.route('/get_otm', methods=['GET'])
def get_otm():
    """医院 A 返回自己的掩码 M_A"""
    return jsonify({"otm": M_A.tolist()})

@app.route('/request_otm_from_B', methods=['GET'])
def request_otm_from_B():
    """医院 A 访问医院 B，获取 B 的掩码，并进行计算"""
    url = "https://127.0.0.1:5001/get_otm"  # 访问医院 B 的端口
    response = requests.get(url, verify=False)  # 获取 B 的掩码
    otm_from_B = np.array(response.json()["otm"])

    # 计算加掩码的参数
    W_A_masked = W_A + M_A  # 先加上 A 的掩码
    W_A_final = W_A_masked - otm_from_B  # 再去掉 B 的掩码

    # 计算哈希值
    W_A_final_hash = hashlib.sha256(W_A_final.tobytes()).hexdigest()

    # 组织 Payload
    payload = {
        "hospital_id": "A",
        "round": 1,  # 训练轮次（后续可从 ML 代码获取）
        "W_final": W_A_final.tolist(),
        "W_final_hash": W_A_final_hash,
        "timestamp": int(time.time()),  # 当前时间戳
    }

    # 用医院 A 的私钥对 payload 进行签名
    payload_str = json.dumps(payload, sort_keys=True).encode("utf-8")  # 规范化 JSON 后签名
    signature = rsa.sign(payload_str, privkey, "SHA-256")  # 生成签名
    payload["signature"] = signature.hex()  # 转成十六进制字符串，方便传输

    # 发送到医院节点
    response = requests.post(HOSPITAL_A_NODE_URL, json=payload, verify=False)

    return jsonify({
        "W_A_final": W_A_final.tolist(),
        "W_A_final_hash": W_A_final_hash,
        "upload_status": response.json()
    })

if __name__ == '__main__':
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain("cert.pem", "key.pem")
    app.run(host='0.0.0.0', port=5000, ssl_context=context)  # 启动 HTTPS