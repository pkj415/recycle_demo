pragma solidity ^0.5.1;

import "node_modules/@openzeppelin/contracts/token/ERC721/ERC721MetadataMintable.sol";
import "Utils.sol";
// import 'node_modules/zeppelin-solidity/contracts/token/ERC721/ERC721Full.sol';

contract PlasticCoin is ERC721MetadataMintable {
    struct User {
        string email;
        string phone;
        bool hasMintingRights;
    }

    struct IndexValue { uint keyIndex; uint value; }
    struct KeyFlag { uint key; bool deleted; }

    struct UserDetails {
        mapping(address => IndexValue) data;
        KeyFlag[] keys;
        uint size;
    }

    UserDetails userDetails;

    // Apply library functions to the data type.
    using IterableMapping for UserDetails;

    address public _minterGranter;

    // Mapping from token ID to owner with their shares
    mapping (uint256 => mapping(address => uint)) private _tokenOwnersShares;
    mapping (uint256 => uint256) tokenIds;
    mapping (uint256 => mapping(address => address)) tokenIdOwnersList;
    mapping (uint256 => uint) tokenIdOwnersCnt;

    // Mapping from owner to tokens with their shares
    // TODO: this won't work, has some issues. Read on this and fix it.
    mapping (address => mapping(uint256 => uint)) private _ownerTokensShares;
    mapping (address => address) ownerAddresses;
    mapping (address => mapping(uint256 => uint256)) ownerTokensList;
    mapping (address => uint) ownerTokensCnt;

    uint public divisibility = 1000;

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

    function mintWithTokenURI(address to, uint256 tokenId, string memory tokenURI) public onlyMinter returns (bool) {
        require(!_exists(tokenId), "Token already exists");
        _mint(to, tokenId);
        _setTokenURI(tokenId, tokenURI);

        _tokenOwnersShares[tokenId][to] = divisibility;
        _ownerTokensShares[to][tokenId] = divisibility;

        // tokenIds[tokenId] = tokenIds[0];
        // tokenIds[0] = tokenId;

        tokenIdOwnersList[tokenId][to] = tokenIdOwnersList[tokenId][address(0)];
        tokenIdOwnersList[tokenId][address(0)] = to;
        tokenIdOwnersCnt[tokenId] += 1;

        // ownerAddresses[to] = ownerAddresses[0x0];
        // ownerAddresses[0x0] = to;

        ownerTokensList[to][tokenId] = ownerTokensList[to][0];
        ownerTokensList[to][0] = tokenId;
        ownerTokensCnt[to] += 1;

        return true;
    }

    function transferShareFrom(address to, uint256 tokenId, uint share) public {
        require(_tokenOwnersShares[tokenId][_msgSender()] >= share, "Cannot share more than owner's share");
        require(to != address(0), "Cannot transfer to the zero address");

        _tokenOwnersShares[tokenId][_msgSender()] -= share;
        _ownerTokensShares[_msgSender()][tokenId] -= share;

        if (_tokenOwnersShares[tokenId][_msgSender()] == 0) {
            // TODO: Remove from mappings if share reaches 0
            // Warning: unbounded gas loop
            // while (llIndex[parent] != _addr) parent = llIndex[parent];

            // llIndex[parent] = llIndex[ llIndex[parent]];
            // delete llIndex[_addr];
            // delete balances[_addr];
        }
        if (_tokenOwnersShares[tokenId][to] == 0) {
            tokenIdOwnersList[tokenId][to] = tokenIdOwnersList[tokenId][address(0)];
            tokenIdOwnersList[tokenId][address(0)] = to;
            tokenIdOwnersCnt[tokenId] += 1;

            ownerTokensList[to][tokenId] = ownerTokensList[to][0];
            ownerTokensList[to][0] = tokenId;
            ownerTokensCnt[to] += 1;
        }

        _tokenOwnersShares[tokenId][to] += share;
        _ownerTokensShares[to][tokenId] += share;

        // TODO: Emit events
    }

    function getTokenOwners(uint256 tokenId) public view returns (address[] memory) {
        address[] memory ret = new address[](tokenIdOwnersCnt[tokenId]);
        address current = tokenIdOwnersList[tokenId][address(0)];
        uint i = 0;
        while (current != address(0)) {
            ret[i] = current;
            current = tokenIdOwnersList[tokenId][current];
            i++;
        }
        return ret;
    }

    function getTokenShare(uint256 tokenId, address owner_address) public view returns (uint) {
        return _tokenOwnersShares[tokenId][owner_address];
    }

    function getOwnerTokens(address owner) public view returns (uint256[] memory) {
        uint256[] memory ret = new uint256[](ownerTokensCnt[owner]);
        // address current = tokenIdOwnersList[tokenId][address(0)];
        uint256 current = ownerTokensList[owner][0];
        uint i = 0;
        while (current != 0) {
            ret[i] = current;
            current = ownerTokensList[owner][current];
            i++;
        }
        return ret;
    }

    function insertUserDetails(string email, string phone) public {
        uint256 memory hasMintingRights = false;

        require(userDetails.contains(_msgSender()) == false, "The user details already exist.");
        userDetails.insert(_msgSender(), User({email: email, phone: phone, hasMintingRights: hasMintingRights}));
    }
}