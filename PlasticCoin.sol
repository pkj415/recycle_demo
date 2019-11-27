pragma solidity ^0.5.1;

import "token/ERC721/ERC721MetadataMintable.sol";
// import 'node_modules/zeppelin-solidity/contracts/token/ERC721/ERC721Full.sol';

contract PlasticCoin is ERC721MetadataMintable {
    address public _minterGranter;
    constructor() ERC721Metadata("PlasticCoin", "PLC") ERC721() public {
        _minterGranter = _msgSender();
    }

    modifier onlyMinterGranter() {
        require(_msgSender() == _minterGranter, "Caller does not have the rights to grant Minter role");
        _;
    }

    function addMinter(address account) public onlyMinterGranter {
        _addMinter(account);
    }

    function renounceMinter(address account) public onlyMinterGranter {
        _removeMinter(account);
    }
}