from fastapi import FastAPI
from web3 import Web3
import json

app = FastAPI()

# 连接本地 Ganache 区块链
web3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

# 读取智能合约 ABI
contract_address = "0x3f0D4De8B5e0cf2Ded536e87DfC22c9e2Ce04062"  # <-- 这里换成你的合约地址
contract_abi = json.loads(open("build/contracts/FLMetadata.json", encoding="utf-8").read())["abi"]
contract = web3.eth.contract(address=contract_address, abi=contract_abi)

# 账户
owner_account = web3.eth.accounts[0]

### 🚀 1. 医院提交训练数据
@app.post("/add_training")
async def add_training(data: dict):
    tx_hash = contract.functions.addTrainingRound(
        data["hospital"], data["timestamp"], data["maskHash"], data["signature"]
    ).transact({"from": owner_account})
    return {"tx_hash": tx_hash.hex()}

### 🚀 2. 记录全局模型哈希
@app.post("/set_model_hash")
async def set_model_hash(data: dict):
    tx_hash = contract.functions.setAggregatedModelHash(
        data["roundNumber"], data["globalModelHash"]
    ).transact({"from": owner_account})
    return {"tx_hash": tx_hash.hex()}

### 🚀 3. 查询训练数据
@app.get("/get_training/{round_number}")
async def get_training(round_number: int):
    result = contract.functions.getTrainingRound(round_number).call()
    return {
        "roundNumber": result[0],
        "hospitalName": result[1],
        "timestamp": result[2],
        "maskIngredientsHash": result[3],
        "hospitalSignature": result[4]
    }

### 🚀 4. 验证医院签名
@app.get("/verify_signature/{round_number}/{signature}")
async def verify_signature(round_number: int, signature: str):
    is_valid = contract.functions.verifySignature(round_number, signature).call()
    return {"isValid": is_valid}

# 运行服务器
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000)