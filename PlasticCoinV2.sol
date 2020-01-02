pragma solidity ^0.5.1;

import "node_modules/@openzeppelin/contracts/token/ERC721/ERC721MetadataMintable.sol";
import "node_modules/@openzeppelin/upgrades/contracts/upgradeability/BaseAdminUpgradeabilityProxy.sol";

contract PlasticCoinV2 is ERC721MetadataMintable, BaseAdminUpgradeabilityProxy {

    address implementation;

    struct User {
        string email;
        string phone;
        bool hasMintingRight;
    }

    struct IndexValue { uint keyIndex; User value; }
    struct KeyFlag { address key; bool deleted; }

    struct UserDetails {
        mapping(address => IndexValue) data;
        KeyFlag[] keys;
        uint size;
    }

    struct PlasticCoinStruct {
        address[] minters;
        UserDetails userDetails;

        address minterGranter;
        // Mapping from token ID to owner with their shares
        mapping (uint256 => mapping(address => uint)) tokenOwnersShares;
        mapping (uint256 => uint256) tokenIds;
        mapping (uint256 => mapping(address => address)) tokenIdOwnersList;
        mapping (uint256 => uint) tokenIdOwnersCnt;

        // Mapping from owner to tokens with their shares
        // TODO: this won't work, has some issues. Read on this and fix it.
        mapping (address => mapping(uint256 => uint)) ownerTokensShares;
        mapping (address => address) ownerAddresses;
        mapping (address => mapping(uint256 => uint256)) ownerTokensList;
        mapping (address => uint) ownerTokensCnt;

        // TODO: Support any value of share cnt in the functions.
        mapping (uint256 => uint) tokenShareCnt;
    }

    PlasticCoinStruct plasticCoinStruct;

    constructor () ERC721Metadata("PlasticCoin", "PLC") ERC721() public {
        plasticCoinStruct.minterGranter = _msgSender();
        // require(true == false, "THERE");
        // plasticCoinLibrary = PlasticCoinLibrary(plasticCoinLibraryAddress)
        //        plasticCoinStruct.initializeContract(_msgSender());
    }

    function insertUser(address key, User memory value) internal returns (bool replaced) {
        uint keyIndex = plasticCoinStruct.userDetails.data[key].keyIndex;
        plasticCoinStruct.userDetails.data[key].value = value;
        if (keyIndex > 0)
            return true;
        else {
            plasticCoinStruct.userDetails.keys.push(KeyFlag({key: key, deleted: false}));
            keyIndex = plasticCoinStruct.userDetails.keys.length;
            plasticCoinStruct.userDetails.data[key].keyIndex = keyIndex;
            plasticCoinStruct.userDetails.keys[keyIndex-1].key = key;
            plasticCoinStruct.userDetails.size++;
            return false;
        }
    }

    function containsUser(address key) internal view returns (bool) {
        return plasticCoinStruct.userDetails.data[key].keyIndex > 0;
    }
    
    modifier onlyMinterGranter() {
        require(_msgSender() == plasticCoinStruct.minterGranter, "Caller does not have the rights to grant Minter role");
        _;
    }

    function addMinter(address account) public onlyMinterGranter {
        _addMinter(account);
    }

    function renounceMinter(address account) public onlyMinterGranter {
        _removeMinter(account);
    }

    function mintWithTokenURI(address to, uint256 tokenId, string memory tokenURI) public onlyMinter returns (bool) {
        require(!_exists(tokenId), "Token already exists");
        _mint(to, tokenId);
        _setTokenURI(tokenId, tokenURI);

        plasticCoinStruct.tokenOwnersShares[tokenId][to] = 1000;
        plasticCoinStruct.ownerTokensShares[to][tokenId] = 1000;
        plasticCoinStruct.tokenShareCnt[tokenId] = 1000;

        // tokenIds[tokenId] = tokenIds[0];
        // tokenIds[0] = tokenId;

        plasticCoinStruct.tokenIdOwnersList[tokenId][to] = plasticCoinStruct.tokenIdOwnersList[tokenId][address(0)];
        plasticCoinStruct.tokenIdOwnersList[tokenId][address(0)] = to;
        plasticCoinStruct.tokenIdOwnersCnt[tokenId] += 1;

        // ownerAddresses[to] = ownerAddresses[0x0];
        // ownerAddresses[0x0] = to;

        plasticCoinStruct.ownerTokensList[to][tokenId] = plasticCoinStruct.ownerTokensList[to][0];
        plasticCoinStruct.ownerTokensList[to][0] = tokenId;
        plasticCoinStruct.ownerTokensCnt[to] += 1;

        return true;
    }

    function transferShareFrom(address to, uint256 tokenId, uint share) public {
        require(plasticCoinStruct.tokenOwnersShares[tokenId][_msgSender()] >= share, "Cannot share more than owner's share");
        require(to != address(0), "Cannot transfer to the zero address");

        plasticCoinStruct.tokenOwnersShares[tokenId][_msgSender()] -= share;
        plasticCoinStruct.ownerTokensShares[_msgSender()][tokenId] -= share;

        if (plasticCoinStruct.tokenOwnersShares[tokenId][_msgSender()] == 0) {
            // TODO: Remove from mappings if share reaches 0
            // Warning: unbounded gas loop
            // while (llIndex[parent] != _addr) parent = llIndex[parent];

            // llIndex[parent] = llIndex[ llIndex[parent]];
            // delete llIndex[_addr];
            // delete balances[_addr];
        }
        if (plasticCoinStruct.tokenOwnersShares[tokenId][to] == 0) {
            plasticCoinStruct.tokenIdOwnersList[tokenId][to] = plasticCoinStruct.tokenIdOwnersList[tokenId][address(0)];
            plasticCoinStruct.tokenIdOwnersList[tokenId][address(0)] = to;
            plasticCoinStruct.tokenIdOwnersCnt[tokenId] += 1;

            plasticCoinStruct.ownerTokensList[to][tokenId] = plasticCoinStruct.ownerTokensList[to][0];
            plasticCoinStruct.ownerTokensList[to][0] = tokenId;
            plasticCoinStruct.ownerTokensCnt[to] += 1;
        }

        plasticCoinStruct.tokenOwnersShares[tokenId][to] += share;
        plasticCoinStruct.ownerTokensShares[to][tokenId] += share;

        // TODO: Emit events
    }

    function getTokenOwners(uint256 tokenId) public view returns (address[] memory) {
        address[] memory ret = new address[](plasticCoinStruct.tokenIdOwnersCnt[tokenId]);
        address current = plasticCoinStruct.tokenIdOwnersList[tokenId][address(0)];
        uint i = 0;
        while (current != address(0)) {
            ret[i] = current;
            current = plasticCoinStruct.tokenIdOwnersList[tokenId][current];
            i++;
        }
        return ret;
    }

    function getTokenShare(uint256 tokenId, address owner_address) public view returns (uint) {
        return plasticCoinStruct.tokenOwnersShares[tokenId][owner_address];
    }

    function getOwnerTokens(address owner) public view returns (uint256[] memory) {
        uint256[] memory ret = new uint256[](plasticCoinStruct.ownerTokensCnt[owner]);
        // address current = tokenIdOwnersList[tokenId][address(0)];
        uint256 current = plasticCoinStruct.ownerTokensList[owner][0];
        uint i = 0;
        while (current != 0) {
            ret[i] = current;
            current = plasticCoinStruct.ownerTokensList[owner][current];
            i++;
        }
        return ret;
    }

    event addedUser(address user_address);
    function insertUserDetails(string memory email, string memory phone, bool hasMintingRight) public {
        require(containsUser(_msgSender()) == true, "The user details already exist.");
        insertUser(_msgSender(), User({email: email, phone: phone, hasMintingRight: hasMintingRight}));

        emit addedUser(_msgSender());
    }

    function getUserDetails(address key) public view returns (string memory, string memory, bool hasMintingRight) {
//        require(contains(userDetails, _msgSender()) == true, "The user details don't exist.");
        return (plasticCoinStruct.userDetails.data[key].value.email, plasticCoinStruct.userDetails.data[key].value.phone, plasticCoinStruct.userDetails.data[key].value.hasMintingRight);
    }
    // function addMinter(PlasticCoinStruct storage self, address account) internal {

    // }
}

// contract PlasticCoinProxy is PlasticCoin {
    
//     constructor (address implementationAddress) PlasticCoin() public {
//          implementation = implementationAddress;
//     }

//     function setImplementation(address newImplementation) public {
//         implementation = newImplementation;
//     }

//     function getImplementation() public view returns (address){
//         return implementation;
//     }
// }
