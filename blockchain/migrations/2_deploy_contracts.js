const IncentiveScheme = artifacts.require("IncentiveScheme");

module.exports = function (deployer) {    
    deployer.deploy(IncentiveScheme, {value: web3.utils.toWei("10", "ether")});
};
