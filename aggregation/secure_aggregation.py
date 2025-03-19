import json
import subprocess
import hashlib
import requests
import numpy as np

# IPFS-related functions
def get_from_ipfs(cid):
    """Retrieve file content from IPFS"""
    print(f" Fetching data from IPFS: {cid}")

    try:
        result = subprocess.run(
            "C:\\Users\\Administrator\\Desktop\\kubo\\ipfs cat " + cid,
            shell=True, capture_output=True, text=True, check=True, timeout=10
        )
        data = json.loads(result.stdout)
        print(f"Successfully retrieved data from IPFS, first 50 characters: {result.stdout[:50]} ...")
        return data
    except subprocess.TimeoutExpired:
        print(f"IPFS fetch timeout (CID: {cid}). Please check if the IPFS daemon is running.")
    except subprocess.CalledProcessError as e:
        print(f" IPFS retrieval failed: {e.stderr}")
    except json.JSONDecodeError:
        print(f"JSON parsing failed, returned content: {result.stdout[:100]} ...")

    return None

def add_to_ipfs(data, filename="global_model.json"):
    """Store data in IPFS"""
    print(" Storing data in IPFS...")

    with open(filename, "w") as f:
        json.dump(data, f)

    try:
        result = subprocess.run(
            "C:\\Users\\Administrator\\Desktop\\kubo\\ipfs add " + filename,
            shell=True, capture_output=True, text=True, check=True, timeout=10
        )
        cid = result.stdout.split()[1]  
        print(f"Data stored in IPFS, CID: {cid}")
        return cid
    except subprocess.TimeoutExpired:
        print(" IPFS storage timeout. Please check if the IPFS daemon is running.")
    except subprocess.CalledProcessError as e:
        print(f" Failed to store data in IPFS: {e.stderr}")

    return None

# Blockchain interaction function
def send_to_blockchain(round_number, model_hash):
    """Submit global model hash to the blockchain"""
    print(f"Sending global model hash to blockchain: {model_hash}")
    
    payload = {
        "roundNumber": round_number,
        "globalModelHash": model_hash
    }
    
    try:
        response = requests.post("http://127.0.0.1:5000/set_model_hash", json=payload, timeout=10)
        if response.status_code == 200:
            print(" Successfully stored in the blockchain:", response.json())
        else:
            print(f"Blockchain storage failed: {response.text}")
    except requests.RequestException as e:
        print(f"Blockchain request failed: {e}")

# Secure aggregation function
def secure_aggregation(data1, data2):
    """Perform secure aggregation (mean) and normalization"""
    if not data1 or not data2:
        print("Data is empty. Secure aggregation cannot proceed.")
        return None

    print(" Performing secure aggregation...")

    try:
        bias1, weights1 = np.array(data1["bias"]), np.array(data1["weights"])
        bias2, weights2 = np.array(data2["bias"]), np.array(data2["weights"])

        # Compute aggregated results
        global_bias = (bias1 + bias2) / 2
        global_weights = (weights1 + weights2) / 2

        # Normalize global weights
        norm_factor = np.linalg.norm(global_weights)
        if norm_factor > 0:
            global_weights /= norm_factor

        print(f"Secure aggregation complete | Bias: {global_bias} | First 5 weight values: {global_weights[:5]}")

        return {"global_bias": global_bias.tolist(), "global_weights": global_weights.tolist()}
    except Exception as e:
        print(f" Secure aggregation failed: {e}")
        return None

# Execution of secure aggregation process
def main():
    hospitalA_cid = "QmPX7CQSDB1FpbkWWgLZd7fdypJZVca6sAnQ3vgy3ovHZU"
    hospitalB_cid = "QmcoQ7hu9TGBpxxWBUBg63M3f67T6D7zzyjB2QUBE7qJN5"

    # Fetch data from IPFS
    hospitalA_data = get_from_ipfs(hospitalA_cid)
    hospitalB_data = get_from_ipfs(hospitalB_cid)

    if not hospitalA_data or not hospitalB_data:
        print("Failed to fetch hospital data. Exiting secure aggregation.")
        return

    #  Perform secure aggregation
    global_model = secure_aggregation(hospitalA_data, hospitalB_data)
    if not global_model:
        return

    # 3Store aggregated model in IPFS
    global_model_cid = add_to_ipfs(global_model)
    if global_model_cid:
        print(f"Global model stored in IPFS, CID: {global_model_cid}")

        # Compute hash and store in blockchain
        model_hash = hashlib.sha256(json.dumps(global_model).encode()).hexdigest()
        send_to_blockchain(round_number=1, model_hash=model_hash)

if __name__ == "__main__":
    main()
