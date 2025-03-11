import hashlib
import time
import json
import rsa
import requests  # 需要 requests 库
import ssl
import numpy as np
from flask import Flask, jsonify

app = Flask(__name__)

# 假设的超参数（1×6 向量）
hyperparams = {
    "bootstrap": True,  # 二值
    "max_depth": None,  # 可能是 None
    "max_features": "sqrt",  # 字符串
    "min_samples_leaf": 4,  # 数值
    "min_samples_split": 10,  # 数值
    "n_estimators": 100  # 数值
}

# 1️ 计算哈希掩码（不需要交换）
def hash_value(value):
    return hashlib.sha256(str(value).encode()).hexdigest()

hashed_hyperparams = {
    "bootstrap": hash_value(hyperparams["bootstrap"]),
    "max_depth": hash_value("None"),  # 统一哈希 None
    "max_features": hash_value(hyperparams["max_features"])
}

# 2️ 生成随机掩码（仅数值参数需要交换）
random_mask = {
    "min_samples_leaf": np.random.randint(-10, 10),
    "min_samples_split": np.random.randint(-10, 10),
    "n_estimators": np.random.randint(-10, 10)
}

# 计算 Masked 超参数（数值参数 + 哈希参数）
masked_values = {
    **hashed_hyperparams,  # 直接包含哈希的参数
    "min_samples_leaf": hyperparams["min_samples_leaf"] + random_mask["min_samples_leaf"],
    "min_samples_split": hyperparams["min_samples_split"] + random_mask["min_samples_split"],
    "n_estimators": hyperparams["n_estimators"] + random_mask["n_estimators"]
}

# 计算 `masked_values` 的哈希值
masked_values_hash = hashlib.sha256(json.dumps(masked_values, sort_keys=True).encode()).hexdigest()

HOSPITAL_A_NODE_URL = "https://127.0.0.1:5002/upload"

# 读取私钥（用于签名）
with open("hospital_A_private.pem", "rb") as priv_file:
    privkey = rsa.PrivateKey.load_pkcs1(priv_file.read())

@app.route('/get_otm', methods=['GET'])
def get_otm():
    """医院 A 返回自己的数值掩码"""
    return jsonify({"otm": random_mask})

@app.route('/request_otm_from_B', methods=['GET'])
def request_otm_from_B():
    """医院 A 访问医院 B，获取 B 的掩码，并进行计算"""
    url = "https://127.0.0.1:5001/get_otm"  # 访问医院 B 的端口
    response = requests.get(url, verify=False)  # 获取 B 的掩码
    otm_from_B = response.json()["otm"]

    # 计算最终的掩码梯度（抵消 A 和 B 的随机掩码）
    final_masked_values = {
        "bootstrap": masked_values["bootstrap"],  # 保持哈希值
        "max_depth": masked_values["max_depth"],
        "max_features": masked_values["max_features"],
        "min_samples_leaf": masked_values["min_samples_leaf"] - otm_from_B["min_samples_leaf"],
        "min_samples_split": masked_values["min_samples_split"] - otm_from_B["min_samples_split"],
        "n_estimators": masked_values["n_estimators"] - otm_from_B["n_estimators"]
    }

    # 重新计算 `masked_values_hash`
    final_masked_values_hash = hashlib.sha256(json.dumps(final_masked_values, sort_keys=True).encode()).hexdigest()

    # 组织 Payload
    payload = {
        "hospital_id": "A",
        "round": 1,  # 训练轮次
        "masked_values": final_masked_values,
        "masked_values_hash": final_masked_values_hash,
        "timestamp": int(time.time()),  # 当前时间戳
    }

    # 用医院 A 的私钥对 payload 进行签名
    payload_str = json.dumps(payload, sort_keys=True).encode("utf-8")  # 规范化 JSON 后签名
    signature = rsa.sign(payload_str, privkey, "SHA-256")  # 生成签名
    payload["signature"] = signature.hex()  # 转成十六进制字符串，方便传输

    # 发送到医院节点
    response = requests.post(HOSPITAL_A_NODE_URL, json=payload, verify=False)

    return jsonify({
        "masked_values": final_masked_values,
        "masked_values_hash": final_masked_values_hash,
        "upload_status": response.json()
    })

if __name__ == '__main__':
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain("cert.pem", "key.pem")
    app.run(host='0.0.0.0', port=5000, ssl_context=context)  # 启动 HTTPS
