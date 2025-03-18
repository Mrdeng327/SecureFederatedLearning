const FLMetadata = artifacts.require("FLMetadata");

module.exports = function (deployer) {
  deployer.deploy(FLMetadata);
};
