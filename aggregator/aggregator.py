from web3 import Web3
import json
import requests
import numpy as np
import rsa

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import base64

LOCAL_IPFS_API = "http://127.0.0.1:5001/api/v0/add"
IPFS_RETRIEVAL = "http://127.0.0.1:8080/ipfs/"

# Connect to web3
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:7545'))
CONTRACT_ADDRESS = "0x16d8FD14D7521202161089276450b37b5cE3F548"
with open("blockchain/build/contracts/IncentiveScheme.json", "r") as f:
    contract_json = json.load(f)

contract_abi = contract_json["abi"]
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)
OWNER_ADDRESS = w3.eth.accounts[0]
PRIVATE_KEY = "0x2009915365d59054ff570c0d8b2fc7b767a01c80aed09e67ee370dc0ef47ba1c"

with open("aggregator/aggregator_private.pem", "rb") as priv_file:
    privkey = rsa.PrivateKey.load_pkcs1(priv_file.read())

def register_participant(participant_address, name):
    tx = contract.functions.registerParticipant(participant_address, name).build_transaction({
        "from": OWNER_ADDRESS,
        "nonce": w3.eth.get_transaction_count(OWNER_ADDRESS),
    })

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Participant {participant_address} registered successfully")
    print(f"Transaction Hash: {receipt.transactionHash.hex()}")


# Get registered participants from the smart contract
def get_registered_participants():
    participant_count = contract.functions.participantCount().call()
    participants = []

    for i in range(participant_count):
        address = contract.functions.participantAddrs(i).call()
        participant_data = contract.functions.participants(address).call()
        participants.append({
            "address": address,
            "name": participant_data[0],
            "reputation": participant_data[1],
            "exists": participant_data[2],
            "gradient_cid": participant_data[3],
            "stake": participant_data[4],
            "submitted": participant_data[5],
            "evaluation": participant_data[6],
            "permittedToGlobalModel": participant_data[7],
            "globalModelCID": participant_data[8]
        })
    
    return participants


# Get data stored in IPFS
def retrieve_from_ipfs(cid):
    url = f"{IPFS_RETRIEVAL}{cid}"
    response = requests.get(url)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch data from IPFS for CID: {cid}")
        return None
    

# Upload data to IPFS
def upload_to_ipfs(data):
    json_data = json.dumps(data) 
    response = requests.post(LOCAL_IPFS_API, files={"file": ("data.json", json_data, "application/json")})
    if response.status_code == 200:
        return response.json()["Hash"]
    else:
        print(f"Failed to upload data to IPFS: {response.text}")
        return None


def decrypt_with_aggregator_key(encrypted_data):
    encrypted_key = base64.b64decode(encrypted_data["aes_key"])
    decrypted_key = rsa.decrypt(encrypted_key, privkey) 

    nonce = base64.b64decode(encrypted_data["nonce"])
    ciphertext = base64.b64decode(encrypted_data["ciphertext"])
    tag = base64.b64decode(encrypted_data["tag"])
    
    cipher = AES.new(decrypted_key, AES.MODE_GCM, nonce=nonce)
    decrypted_data = cipher.decrypt_and_verify(ciphertext, tag)
    
    return json.loads(decrypted_data.decode("utf-8"))


def encrypt_with_participant_key(data, public_key_path):
    with open(public_key_path, "rb") as f:
        pubkey = rsa.PublicKey.load_pkcs1(f.read())
    key = get_random_bytes(16) 
    cipher = AES.new(key, AES.MODE_GCM)
    ciphertext, tag = cipher.encrypt_and_digest(data.encode("utf-8"))

    encrypted_key = rsa.encrypt(key, pubkey)
    
    return {
        "aes_key": base64.b64encode(encrypted_key).decode(), 
        "ciphertext": base64.b64encode(ciphertext).decode(),
        "nonce": base64.b64encode(cipher.nonce).decode(),
        "tag": base64.b64encode(tag).decode()
    }


def evaluate_contributions():
    participants = get_registered_participants()
    participant_acc_improvements = {}

    for participant in participants:
        cid = participant["gradient_cid"]
        data = retrieve_from_ipfs(cid)

        acc_improvement = data["acc_improvement"]
        participant_acc_improvements[participant["address"]] = int(acc_improvement*1000)

    return participant_acc_improvements


def submit_evaluations(evaluations):
    addresses = list(evaluations.keys())
    scores = list(evaluations.values())  

    tx = contract.functions.submitContributionEvaluations(addresses, scores).build_transaction({
        "from": OWNER_ADDRESS,
        "nonce": w3.eth.get_transaction_count(OWNER_ADDRESS),
    })

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Transaction Hash: {receipt.transactionHash.hex()}")


def aggregate_gradients():
    participants = get_registered_participants()
    
    aggregated_weights = None
    aggregated_bias = 0

    for participant in participants:
        cid = participant["gradient_cid"]
        data = retrieve_from_ipfs(cid)

        encrypted_weights = data["masked_weights"]
        encrypted_bias = data["masked_bias"]

        decrypted_weights_json = decrypt_with_aggregator_key(encrypted_weights)
        decrypted_bias_json = decrypt_with_aggregator_key(encrypted_bias)

        weights = np.array(decrypted_weights_json)
        bias = float(decrypted_bias_json)

        if aggregated_weights is None:
            aggregated_weights = weights
        else:
            aggregated_weights += weights

        aggregated_bias += bias

    return aggregated_weights, aggregated_bias


def submit_global_model(global_weights, global_bias):
    participants = get_registered_participants()
    permitted_participants = [p for p in participants if p["permittedToGlobalModel"]]

    global_model = {
        "weights": global_weights.tolist(),
        "bias": global_bias
    }
    global_model_json = json.dumps(global_model)

    for participant in permitted_participants:
        public_key_path = f"public_keys/{participant['name']}_public.pem"
        encrypted_global_model = encrypt_with_participant_key(global_model_json, public_key_path)
        cid = upload_to_ipfs(encrypted_global_model)

        tx = contract.functions.submitGlobalModelCID(participant["address"], cid).build_transaction({
            "from": OWNER_ADDRESS,
            "nonce": w3.eth.get_transaction_count(OWNER_ADDRESS),
        })

        signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Transaction Hash: {receipt.transactionHash.hex()}")


# Test function for demonstrative purposes. 
# The aggregator wouldn't actually have access to raw gradients.
# Checks if aggregated gradients are correct.
def test_aggregation():
    A_grad_weights = np.load("hospital/Local_Hospital_A/grad_weights.npy")
    A_grad_bias = np.load("hospital/Local_Hospital_A/grad_bias.npy")

    B_grad_weights = np.load("hospital/Local_Hospital_B/grad_weights2_padded.npy")
    B_grad_bias = np.load("hospital/Local_Hospital_B/grad_bias2.npy")

    raw_aggregated_weights = A_grad_weights + B_grad_weights
    raw_aggregated_bias = A_grad_bias + B_grad_bias

    aggregated_weights, aggregated_bias = aggregate_gradients()

    weights_match = np.allclose(raw_aggregated_weights, aggregated_weights)
    bias_match = np.isclose(raw_aggregated_bias, aggregated_bias)

    if weights_match and bias_match:
        print("Test passed: Aggregated weights and biases match the sum of raw gradients.")
    else:
        print("Test failed: Aggregated weights and biases do not match the sum of raw gradients.")
        if not weights_match:
            print("Weights do not match.")
        if not bias_match:
            print("Biases do not match.")


def main():
    # Register test participants
    HOSPITAL_A_ADDRESS = w3.eth.accounts[2]
    HOSPITAL_B_ADDRESS = w3.eth.accounts[3]
    register_participant(HOSPITAL_A_ADDRESS, "hospital_A")
    register_participant(HOSPITAL_B_ADDRESS, "hospital_B")

    # Evaluate contributions and submit to contract
    evaluations = evaluate_contributions()
    print(evaluations)
    submit_evaluations(evaluations)

    # Compute global model
    global_weights, global_bias = aggregate_gradients()

    # Submit to smart contract, encrypted with participants keys
    submit_global_model(global_weights, global_bias)

    participants = get_registered_participants()
    print(participants)

    test_aggregation()
    
    pass


if __name__ == "__main__":
    main()