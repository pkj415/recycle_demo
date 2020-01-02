pragma solidity ^0.5.1;

import "node_modules/@openzeppelin/contracts/token/ERC721/ERC721MetadataMintable.sol";
//import "MinterLib.sol";
//import "Utils.sol";
// import 'node_modules/zeppelin-solidity/contracts/token/ERC721/ERC721Full.sol';

library PlasticCoinLibrary {
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

    struct PlasticCoinStorage {
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

    function initializeContract(PlasticCoinStorage storage self, address msgSender) public {
        self.minterGranter = msgSender;
    }

    function insertUser(PlasticCoinStorage storage self, address key, User memory value) internal returns (bool replaced) {
        uint keyIndex = self.userDetails.data[key].keyIndex;
        self.userDetails.data[key].value = value;
        if (keyIndex > 0)
            return true;
        else {
            self.userDetails.keys.push(KeyFlag({key: key, deleted: false}));
            keyIndex = self.userDetails.keys.length;
            self.userDetails.data[key].keyIndex = keyIndex;
            self.userDetails.keys[keyIndex-1].key = key;
            self.userDetails.size++;
            return false;
        }
    }

    function containsUser(PlasticCoinStorage storage self, address key) internal view returns (bool) {
        return self.userDetails.data[key].keyIndex > 0;
    }
    

    // function addMinter(PlasticCoinStorage storage self, address account) internal {

    // }
}

contract PlasticCoin is ERC721MetadataMintable {

    using PlasticCoinLibrary for PlasticCoinLibrary.PlasticCoinStorage;
    PlasticCoinLibrary.PlasticCoinStorage plasticCoinStorage;

    constructor () ERC721Metadata("PlasticCoin", "PLC") ERC721() public {
        // minterGranter = _msgSender();
        // plasticCoinLibrary = PlasticCoinLibrary(plasticCoinLibraryAddress)
        plasticCoinStorage.initializeContract(_msgSender());
    }

    modifier onlyMinterGranter() {
        require(_msgSender() == plasticCoinStorage.minterGranter, "Caller does not have the rights to grant Minter role");
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

        plasticCoinStorage.tokenOwnersShares[tokenId][to] = 1000;
        plasticCoinStorage.ownerTokensShares[to][tokenId] = 1000;
        plasticCoinStorage.tokenShareCnt[tokenId] = 1000;

        // tokenIds[tokenId] = tokenIds[0];
        // tokenIds[0] = tokenId;

        plasticCoinStorage.tokenIdOwnersList[tokenId][to] = plasticCoinStorage.tokenIdOwnersList[tokenId][address(0)];
        plasticCoinStorage.tokenIdOwnersList[tokenId][address(0)] = to;
        plasticCoinStorage.tokenIdOwnersCnt[tokenId] += 1;

        // ownerAddresses[to] = ownerAddresses[0x0];
        // ownerAddresses[0x0] = to;

        plasticCoinStorage.ownerTokensList[to][tokenId] = plasticCoinStorage.ownerTokensList[to][0];
        plasticCoinStorage.ownerTokensList[to][0] = tokenId;
        plasticCoinStorage.ownerTokensCnt[to] += 1;

        return true;
    }

    function transferShareFrom(address to, uint256 tokenId, uint share) public {
        require(plasticCoinStorage.tokenOwnersShares[tokenId][_msgSender()] >= share, "Cannot share more than owner's share");
        require(to != address(0), "Cannot transfer to the zero address");

        plasticCoinStorage.tokenOwnersShares[tokenId][_msgSender()] -= share;
        plasticCoinStorage.ownerTokensShares[_msgSender()][tokenId] -= share;

        if (plasticCoinStorage.tokenOwnersShares[tokenId][_msgSender()] == 0) {
            // TODO: Remove from mappings if share reaches 0
            // Warning: unbounded gas loop
            // while (llIndex[parent] != _addr) parent = llIndex[parent];

            // llIndex[parent] = llIndex[ llIndex[parent]];
            // delete llIndex[_addr];
            // delete balances[_addr];
        }
        if (plasticCoinStorage.tokenOwnersShares[tokenId][to] == 0) {
            plasticCoinStorage.tokenIdOwnersList[tokenId][to] = plasticCoinStorage.tokenIdOwnersList[tokenId][address(0)];
            plasticCoinStorage.tokenIdOwnersList[tokenId][address(0)] = to;
            plasticCoinStorage.tokenIdOwnersCnt[tokenId] += 1;

            plasticCoinStorage.ownerTokensList[to][tokenId] = plasticCoinStorage.ownerTokensList[to][0];
            plasticCoinStorage.ownerTokensList[to][0] = tokenId;
            plasticCoinStorage.ownerTokensCnt[to] += 1;
        }

        plasticCoinStorage.tokenOwnersShares[tokenId][to] += share;
        plasticCoinStorage.ownerTokensShares[to][tokenId] += share;

        // TODO: Emit events
    }

    function getTokenOwners(uint256 tokenId) public view returns (address[] memory) {
        address[] memory ret = new address[](plasticCoinStorage.tokenIdOwnersCnt[tokenId]);
        address current = plasticCoinStorage.tokenIdOwnersList[tokenId][address(0)];
        uint i = 0;
        while (current != address(0)) {
            ret[i] = current;
            current = plasticCoinStorage.tokenIdOwnersList[tokenId][current];
            i++;
        }
        return ret;
    }

    function getTokenShare(uint256 tokenId, address owner_address) public view returns (uint) {
        return plasticCoinStorage.tokenOwnersShares[tokenId][owner_address];
    }

    function getOwnerTokens(address owner) public view returns (uint256[] memory) {
        uint256[] memory ret = new uint256[](plasticCoinStorage.ownerTokensCnt[owner]);
        // address current = tokenIdOwnersList[tokenId][address(0)];
        uint256 current = plasticCoinStorage.ownerTokensList[owner][0];
        uint i = 0;
        while (current != 0) {
            ret[i] = current;
            current = plasticCoinStorage.ownerTokensList[owner][current];
            i++;
        }
        return ret;
    }

    event addedUser(address user_address);
    function insertUserDetails(string memory email, string memory phone, bool hasMintingRight) public {
        require(plasticCoinStorage.containsUser(_msgSender()) == false, "The user details already exist.");
        plasticCoinStorage.insertUser(_msgSender(), PlasticCoinLibrary.User({email: email, phone: phone, hasMintingRight: hasMintingRight}));

        emit addedUser(_msgSender());
    }

    function getUserDetails(address key) public view returns (string memory, string memory, bool hasMintingRight) {
//        require(contains(userDetails, _msgSender()) == true, "The user details don't exist.");
        return (plasticCoinStorage.userDetails.data[key].value.email, plasticCoinStorage.userDetails.data[key].value.phone, plasticCoinStorage.userDetails.data[key].value.hasMintingRight);
    }
}