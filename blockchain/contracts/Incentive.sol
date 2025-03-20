// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;


contract IncentiveScheme {

    struct Participant {
        string name;
        uint256 reputationScore;
        bool exists;
        string gradientCID;
        uint256 stake;
        bool submitted;
        int256 evaluation;
        bool permittedToGlobalModel;
        string globalModelCID;
    }

    mapping(address => Participant) public participants;
    address[] public participantAddrs;
    uint256 public participantCount;
    address public owner;
    uint256 public rewardPool;
    uint256 public reward = 0.1 ether;
    uint256 public roundNumber;
    uint256 public submissionCount = 0;
    bool public allSubmitted = false;
    bool public evaluationsSubmitted = false;
    bool public rewardPunishCompleted = false;
    bool public globalModelSubmitted = false;

    event ParticipantRegistered(address participant);
    event ParticipantUnregistered(address participant);
    event GradientSubmitted(address indexed participant, string gradientCID, uint256 stake, uint256 roundNumber);
    event AllParticipantsSubmitted(uint256 roundNumber);
    event EvaluationsSubmitted(uint256 roundNumber);
    event NewRoundStarted(uint256 roundNumber);
    event Rewarded(address participant, uint256 amount, uint256 roundNumber);
    event Punished(address participant, uint256 amount, uint256 roundNumber);
    event NeutralContribution(address participant, uint256 roundNumber);
    event ReputationUpdated(address participant, int256 reputationChange, uint256 roundNumber);
    event GlobalModelSubmitted(address participant, string cid);

    constructor() payable {
        owner = msg.sender;
        roundNumber = 1;
        rewardPool = msg.value;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not contract owner");
        _;
    }

    /**
     * @dev Deposit funds to reward pool.
     */
    function deposit() external payable onlyOwner {
        require(msg.value > 0, "No funds deposited");
        rewardPool += msg.value;
    }

    /**
     * @dev Register a new participant.
     */
    function registerParticipant(address addr, string calldata name) public onlyOwner {
        require(!participants[addr].exists, "Already registered");
        require(participantCount < 2, "Maximum number of participants reached");

        participants[addr] = Participant({
            name: name,
            reputationScore: 0,
            exists: true,
            gradientCID: "",
            stake: 0,
            submitted: false,
            evaluation: 0,
            permittedToGlobalModel: false,
            globalModelCID: ""
        });

        participantAddrs.push(addr);
        participantCount++;
        emit ParticipantRegistered(addr);
    }

    /**
     * @dev Unregister a participant.
     */
    function unregisterParticipant(address addr) public onlyOwner {
        require(participants[addr].exists, "Not registered");

        delete participants[addr];
        for (uint i = 0; i < participantAddrs.length; i++) {
            if (participantAddrs[i] == addr) {
                participantAddrs[i] = participantAddrs[participantAddrs.length - 1];
                participantAddrs.pop();
                break;
            }
        }
        participantCount--;
        emit ParticipantUnregistered(addr);
    }

    /**
     * @dev Get participant details.
     */
    function getParticipant(address addr) public view returns (Participant memory) {
        require(participants[addr].exists, "Participant not registered");
        return participants[addr];
    }

    /**
     * @dev Submit masked gradient.
     */
    function submitGradientUpdate(string calldata gradientCID) external payable {
        require(participants[msg.sender].exists, "Participant not registered");
        require(!participants[msg.sender].submitted, "Already submitted");
        require(msg.value >= 0.1 ether, "Stake too low");

        participants[msg.sender].gradientCID = gradientCID;
        participants[msg.sender].stake = msg.value;
        participants[msg.sender].submitted = true;
        submissionCount++;

        emit GradientSubmitted(msg.sender, gradientCID, msg.value, roundNumber);

        if (submissionCount == participantCount) {
            allSubmitted = true;
            emit AllParticipantsSubmitted(roundNumber);
        }
    }
    
    /**
     * @dev Submit contribution evaluations.
     */
    function submitContributionEvaluations(address[] calldata addresses, int256[] calldata evaluations) external onlyOwner {
        require(allSubmitted, "Not all participants have submitted");
        require(!evaluationsSubmitted, "Evaluations already submitted");
        require(addresses.length == participantCount, "Invalid input");
        require(addresses.length == evaluations.length, "Invalid input");

        for (uint i = 0; i < addresses.length; i++) {
            require(participants[addresses[i]].exists, "Participant not registered");
            participants[addresses[i]].evaluation = evaluations[i];
        }

        evaluationsSubmitted = true;
        emit EvaluationsSubmitted(roundNumber);

        rewardPunish();
    }

    /**
     * @dev Reward or punish accordingly. Update reputation scores.
     */
    function rewardPunish() public onlyOwner {
        require(evaluationsSubmitted, "Evaluations not submitted yet");
        require(!rewardPunishCompleted, "Reward/punish already completed");
    
        for (uint i = 0; i < participantAddrs.length; i++) {
            address pAddr = participantAddrs[i];
            Participant storage p = participants[pAddr];
            int256 pEvaluation = p.evaluation;
            uint256 pStake = p.stake;

            if(pEvaluation > 100) { // 0.1 or 10% improvement
                uint256 totalPayout = reward + pStake;
                require(totalPayout <= rewardPool, "Insufficient funds in reward pool");

                rewardPool -= totalPayout;

                (bool success, ) = pAddr.call{value: totalPayout}("");
                require(success, "Payment failed");

                p.reputationScore += 1;
                p.permittedToGlobalModel = true;

                emit Rewarded(pAddr, totalPayout, roundNumber);
                emit ReputationUpdated(pAddr, 1, roundNumber);

            } else if(pEvaluation < -100) { // 0.1 or 10% degradation
                rewardPool += pStake;

                if(p.reputationScore > 0) {
                    p.reputationScore -= 1; 
                }

                emit Punished(pAddr, pStake, roundNumber);
                emit ReputationUpdated(pAddr, -1, roundNumber);

            } else { // within neutral range
                (bool success, ) = pAddr.call{value: pStake}("");
                require(success, "Refund stake failed");

                emit NeutralContribution(pAddr, roundNumber);
            }
        }

        rewardPunishCompleted = true;
    }

    /**
     * @dev Submit the global model CID for a participant. Encrypted with participants key.
     */
    function submitGlobalModelCID(address participant, string calldata cid) external onlyOwner {
        require(participants[participant].exists, "Participant not registered");
        require(participants[participant].permittedToGlobalModel, "Participant not permitted to access global model");

        participants[participant].globalModelCID = cid;
        globalModelSubmitted = true;

        emit GlobalModelSubmitted(participant, cid);
    }

    /**
     * @dev Start new round.
     */
    function newRound() public onlyOwner {
        require(globalModelSubmitted, "Global models have not been submitted");
        require(participantCount > 0, "No participants registered");

        for (uint i = 0; i < participantAddrs.length; i++) {
            address pAddr = participantAddrs[i];
            Participant storage p = participants[pAddr];

            p.gradientCID = "";
            p.stake = 0;
            p.submitted = false;
            p.evaluation = 0;
            p.permittedToGlobalModel = false;
            p.globalModelCID = "";
        }

        submissionCount = 0;
        allSubmitted = false;
        evaluationsSubmitted = false;
        rewardPunishCompleted = false;
        roundNumber++;

        emit NewRoundStarted(roundNumber);
    }

}
