import json
import os
import subprocess
import hashlib
import requests

# IPFS 相关函数
def get_from_ipfs(cid):
    """ 从 IPFS 获取文件内容 """
    result = subprocess.run(["ipfs", "cat", cid], capture_output=True, text=True)
    if result.returncode == 0:
        return json.loads(result.stdout)
    else:
        print(f"⚠️ 无法获取 IPFS 内容: {result.stderr}")
        return None

def add_to_ipfs(data, filename="global_model.json"):
    """ 将数据存入 IPFS """
    with open(filename, "w") as f:
        json.dump(data, f)
    
    result = result = subprocess.run(["C:\\Users\\Administrator\\Desktop\\kubo\\ipfs", "cat", cid], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.split()[1]  # 返回 CID
    else:
        print(f"⚠️ 存入 IPFS 失败: {result.stderr}")
        return None

# 区块链交互函数
def send_to_blockchain(round_number, model_hash):
    """ 向区块链提交全局模型哈希 """
    payload = {
        "roundNumber": round_number,
        "globalModelHash": model_hash
    }
    response = requests.post("http://127.0.0.1:5000/set_model_hash", json=payload)
    if response.status_code == 200:
        print("✅ 成功存入区块链:", response.json())
    else:
        print("⚠️ 存入区块链失败:", response.text)

# 计算安全聚合
def secure_aggregation(data1, data2):
    """ 计算安全聚合（取均值） """
    bias1, weights1 = data1["bias"], data1["weights"]
    bias2, weights2 = data2["bias"], data2["weights"]

    # 计算聚合结果
    global_bias = (bias1 + bias2) / 2
    global_weights = [(w1 + w2) / 2 for w1, w2 in zip(weights1, weights2)]

    return {"global_bias": global_bias, "global_weights": global_weights}

# 执行安全聚合流程
def main():
    # 设定 IPFS CID
    hospitalA_cid = "QmPX7CQSDB1FpbkWWgLZd7fdypJZVca6sAnQ3vgy3ovHZU"
    hospitalB_cid = "QmcoQ7hu9TGBpxxWBUBg63M3f67T6D7zzyjB2QUBE7qJN5"

    # 从 IPFS 取回数据
    hospitalA_data = get_from_ipfs(hospitalA_cid)
    hospitalB_data = get_from_ipfs(hospitalB_cid)

    if not hospitalA_data or not hospitalB_data:
        print("⚠️ 无法获取医院数据，退出安全聚合")
        return
    
    # 执行安全聚合
    global_model = secure_aggregation(hospitalA_data, hospitalB_data)
    print("🔹 安全聚合结果:", global_model)

    # 存入 IPFS
    global_model_cid = add_to_ipfs(global_model)
    if global_model_cid:
        print(f"✅ 全局模型存入 IPFS，CID: {global_model_cid}")

        # 计算哈希值并存入区块链
        model_hash = hashlib.sha256(json.dumps(global_model).encode()).hexdigest()
        send_to_blockchain(round_number=1, model_hash=model_hash)

if __name__ == "__main__":
    main()
