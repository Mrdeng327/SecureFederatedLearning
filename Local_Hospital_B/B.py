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
EXCHANGE_URL = "https://127.0.0.1:5002/get_otm"  # 交换掩码（医院 A）
NODE_URL = "https://127.0.0.1:5005/upload"  # 上传医院节点 B
ROUND_NUM = 1  # 轮次从 1 开始

# 读取本地梯度
grad_weights = np.load("grad_weights.npy")
grad_bias = np.load("grad_bias.npy")

# 确保 grad_bias 是 NumPy 数组
if isinstance(grad_bias, (float, int)):
    grad_bias = np.array([grad_bias])

# 生成本地掩码
mask_weights = np.random.rand(*grad_weights.shape)  # 保持数组形状
mask_bias = np.random.rand()  # 生成单个随机数

# 读取私钥（用于签名）
with open("hospital_B_private.pem", "rb") as priv_file:
    privkey = rsa.PrivateKey.load_pkcs1(priv_file.read())

# 计算 SHA-256 哈希值
def compute_hash(data):
    return hashlib.sha256(data.tobytes()).hexdigest()

# 生成签名
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

# API: 获取对方医院 A 的掩码
@app.route("/get_otm", methods=["GET"])
def get_otm():
    return jsonify({
        "mask_weights": mask_weights.tolist(),
        "mask_bias": float(mask_bias)  # 解决 AttributeError，确保 JSON 里的是 float
    })

# API: 处理梯度加密 & 上传到医院节点 B
@app.route("/upload_encrypted_gradients", methods=["POST"])
def upload_encrypted_gradients():
    global ROUND_NUM  # 允许修改全局变量

    try:
        # 请求医院 A 获取掩码
        response = requests.get(EXCHANGE_URL, verify=False)  # 调试阶段禁用 SSL 证书验证
        received_data = response.json()
        received_mask_weights = np.array(received_data["mask_weights"])
        received_mask_bias = float(received_data["mask_bias"])  # 确保是 float 类型

        # 计算加密梯度
        encrypted_weights = grad_weights + mask_weights - received_mask_weights
        encrypted_bias = float(grad_bias) + float(mask_bias) - received_mask_bias  # 确保计算正确

        # 计算哈希值
        hash_weights = compute_hash(encrypted_weights)
        hash_bias = compute_hash(np.array([encrypted_bias]))  # 需要 NumPy 数组计算哈希
        timestamp = int(time.time())

        # 生成签名
        signature = sign_data(privkey, HOSPITAL_ID, ROUND_NUM, hash_weights, hash_bias, timestamp)

        # 上传数据到医院节点 B
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
        response = requests.post(NODE_URL, json=payload, verify=False)  # 调试阶段禁用 SSL 证书验证

        # 轮次 +1，确保下一次为新轮次
        ROUND_NUM += 1

        return jsonify(response.json())

    except Exception as e:
        return jsonify({"error": str(e)}), 500




if __name__ == "__main__":
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain("cert.pem", "key.pem")
    app.run(host="0.0.0.0", port=5003, ssl_context=context)
