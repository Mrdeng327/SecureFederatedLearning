from web3 import Web3
import json
import numpy as np
import requests
import time

# 连接区块链
web3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

# 读取智能合约 ABI
contract_address = "0xYourContractAddress"  # 替换为实际部署的合约地址
contract_abi = json.loads(open("build/contracts/FLMetadata.json").read())["abi"]
contract = web3.eth.contract(address=contract_address, abi=contract_abi)

# 监听 AggregationTriggered 事件
def listen_for_aggregation_trigger():
    """监听区块链事件，等待所有医院提交完数据后触发聚合"""
    event_filter = contract.events.TrainingRoundSubmitted.createFilter(fromBlock='latest')
    print("🔍 Listening for hospital submissions...")

    while True:
        entries = event_filter.get_new_entries()
        if entries:
            print(f"📢 Detected {len(entries)} new submissions.")
            check_and_trigger_aggregation()
        time.sleep(5)  # 避免高频轮询

# 检查同轮次医院提交情况
def check_and_trigger_aggregation():
    """检查当前轮次的所有医院是否提交完数据"""
    latest_round = contract.functions.roundCount().call()
    hospital_count = contract.functions.getHospitalSubmissionCount(latest_round).call()

    EXPECTED_HOSPITALS = 2  # 设定必须有2个医院提交
    if hospital_count >= EXPECTED_HOSPITALS:
        print(f"✅ All {EXPECTED_HOSPITALS} hospitals submitted for round {latest_round}. Triggering aggregation...")
        perform_secure_aggregation(latest_round)
    else:
        print(f"⏳ Waiting for all hospitals. Current submissions: {hospital_count}/{EXPECTED_HOSPITALS}")

# 从分布式存储拉取 Mask Ingredients
STORAGE_FETCH_API_URL = "http://distributed-storage.local/api/get_mask_ingredients"

def fetch_mask_ingredients(round_number):
    """从 IPFS / 分布式存储系统获取 Mask Ingredients"""
    print(f"🌐 Fetching mask ingredients for round {round_number}...")
    response = requests.get(f"{STORAGE_FETCH_API_URL}?round_number={round_number}")

    if response.status_code == 200:
        print("✅ Mask ingredients fetched successfully.")
        return response.json()
    else:
        print(f"❌ Failed to fetch mask ingredients. HTTP Status: {response.status_code}")
        return None

# 执行安全聚合
def perform_secure_aggregation(round_number):
    """执行安全聚合，去除掩码计算全局梯度"""
    mask_ingredients = fetch_mask_ingredients(round_number)
    if not mask_ingredients:
        print("❌ Mask ingredients not available. Aborting aggregation.")
        return

    # 初始化全局梯度
    global_gradient = np.zeros_like(mask_ingredients[0]["mask_ingredient"])

    # 计算全局梯度（去掩码）
    for item in mask_ingredients:
        global_gradient += np.array(item["mask_ingredient"])

    print(f"📊 Aggregated Gradient Computed for round {round_number}")

    # 存入区块链 & 分布式存储
    store_global_gradient_in_blockchain(round_number, global_gradient)
    store_global_gradient_in_storage(round_number, global_gradient)

# 存储全局梯度哈希到区块链
def store_global_gradient_in_blockchain(round_number, global_gradient):
    """计算全局模型哈希并存入区块链"""
    global_model_hash = hash(str(global_gradient.tolist()))  # 计算哈希值
    print(f"📌 Storing global model hash {global_model_hash} on blockchain for round {round_number}.")

    tx_hash = contract.functions.setAggregatedModelHash(
        round_number, str(global_model_hash)
    ).transact({"from": web3.eth.accounts[0]})

    tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"✅ Transaction confirmed: {tx_receipt.transactionHash}")

# 存储完整全局梯度到分布式存储
STORAGE_UPLOAD_API_URL = "http://distributed-storage.local/api/upload_global_gradient"

def store_global_gradient_in_storage(round_number, global_gradient):
    """存储完整梯度文本到 IPFS / 分布式存储"""
    print(f"📤 Uploading full aggregated gradient for round {round_number}...")
    
    payload = {
        "round_number": round_number,
        "global_gradient": global_gradient.tolist()
    }

    response = requests.post(STORAGE_UPLOAD_API_URL, json=payload)

    if response.status_code == 200:
        print("✅ Global gradient successfully stored in distributed storage.")
    else:
        print(f"❌ Failed to store global gradient. HTTP Status: {response.status_code}")

# 启动监听
if __name__ == "__main__":
    listen_for_aggregation_trigger()

