// SPDX-License-Identifier: MIT
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;
pragma experimental ABIEncoderV2;

contract FLMetadata {

    struct TrainingRound {
        uint roundNumber;
        string hospitalName;
        string timestamp;
        string maskIngredientsHash;
        string hospitalSignature; //医院签名，用于溯源和验证
    }

    mapping(uint => TrainingRound) public trainingRounds;
    mapping(uint => string) public aggregatedModelHashes; //全局模型hash
    uint public roundCount;
    address public owner;

    constructor() {
        owner = msg.sender;
        roundCount = 0;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Only the owner can perform this action");
        _;
    }

    // 添加训练轮次的元数据和签名
    function addTrainingRound(
        string memory _hospitalName,
        string memory _timestamp,
        string memory _maskIngredientsHash,
        string memory _hospitalSignature
    ) public {
        roundCount += 1;
        trainingRounds[roundCount] = TrainingRound(
            roundCount,
            _hospitalName,
            _timestamp,
            _maskIngredientsHash,
            _hospitalSignature
        );
    }

    // 设置聚合模型哈希
    function setAggregatedModelHash(uint _roundNumber, string memory _globalModelHash) public {
        require(msg.sender == owner, "Only owner can set hash.");
        aggregatedModelHashes[_roundNumber] = _globalModelHash;
    }

    // 根据轮次查询数据
    function getTrainingRound(uint _roundNumber) public view returns (TrainingRound memory) {
        return trainingRounds[_roundNumber];
    }

    // 验证医院签名
    function verifySignature(uint _roundNumber, string memory _signatureToVerify) public view returns (bool) {
        TrainingRound memory round = trainingRounds[_roundNumber];
        return keccak256(bytes(round.hospitalSignature)) == keccak256(bytes(_signatureToVerify));
    }
}
    

