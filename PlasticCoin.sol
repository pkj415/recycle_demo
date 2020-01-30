pragma solidity ^0.5.1;

import "node_modules/@openzeppelin/contracts/token/ERC721/ERC721MetadataMintable.sol";
import "node_modules/@openzeppelin/upgrades/contracts/upgradeability/AdminUpgradeabilityProxy.sol";

contract PlasticCoinStorage {
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
}

contract PlasticCoinProxy is ERC721MetadataMintable, AdminUpgradeabilityProxy, PlasticCoinStorage {

    // TODO: ERC721MetadataMintable has includes a lot of storage. AdminUpgradeabilityProxy has no state variables.
    // PlasticCoinStorage was created to separate out state from the logic, so that it can be used to maintain the same storage structure at both the proxy and implementation
    // contracts.
    // Issue - Since ERC721MetadataMintable is inherited here to have the same storage structure, we are also inheriting methods that might be overwritten in the implementation
    // contract. This will cause the issue that the transaction call will not be caught by the fallback function. To fix this, we have to manually override to redirect the methods
    // specified in ERC721MetadataMintable. For now, I have redirected mintWithTokenURI. Redirect all of them. Also check if modifiers need to be redirected.

    constructor (address _logic, address _admin, bytes memory _data) ERC721Metadata("PlasticCoin", "PLC") ERC721() AdminUpgradeabilityProxy(_logic, _admin, _data) public {
        plasticCoinStruct.minterGranter = msg.sender;
    }

    // TODO: Define events and integrate with the application.
    // event mintedToken(address to, uint256 tokenId, string tokenURI);
    // event dummyEvent(uint);

    // TODO: Links with the large TODO at the start of this contract. Find a better method to avoid clumsy overriding of all methods in ERC721MetadataMintable.
    function mintWithTokenURI(address to, uint256 tokenId, string memory tokenURI) public returns (bool) {
        _fallback();
    }

    // Things tested -
    // 1. Even if mintWithTokenURI above doesn't have the onlyMinter modifier, the modifier in the called function in the implementation will take care of that. So, don't keep any
    // modifiers in this contract's function at all.
    //
    // 2. The modifiers called after a delegate to the implementation's function is done, are those of the implementation itself. This was tested by overriding onlyMinter modifier in this
    // contract to never fail, but we were still not able to mint tokens using a non-minter account.

    // TODO: Redirect the addMinter function.
    // function addMinter(address account) public {
    //     // _fallback();
    // }

    // TODO: Override the below function to allow fallback and then delegate even if the call is made by the admin. Make a choice on this later (decide on the user dynamics and then
    // change this function). Also, note that the super has also been commneted out, which is not a good pratice?
    function _willFallback() internal {
        // super._willFallback();
    }

    // TODO: Allow the implementation contract to override BaseAdminUpgradeabilityProxy to allow voting etc.

}

contract PlasticCoinV1 is ERC721MetadataMintable, PlasticCoinStorage {
    
    constructor () ERC721Metadata("PlasticCoin", "PLC") ERC721() public {
        // We should ideally not require the below line. The storage of the proxy contract should always be used. But removing the below line breaks things. Fix that.
        plasticCoinStruct.minterGranter = _msgSender();
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
        // _addMinter(account);
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
        return 0;
    }

    function getOwnerTokens(address owner) public view returns (uint256[] memory) {
        uint256[] memory ret = new uint256[](plasticCoinStruct.ownerTokensCnt[owner]);
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
        require(containsUser(_msgSender()) == false, "The user details already exist.");
        insertUser(_msgSender(), User({email: email, phone: phone, hasMintingRight: hasMintingRight}));

        emit addedUser(_msgSender());
    }

    function getUserDetails(address key) public view returns (string memory, string memory, bool) {
        return (plasticCoinStruct.userDetails.data[key].value.email, plasticCoinStruct.userDetails.data[key].value.phone, plasticCoinStruct.userDetails.data[key].value.hasMintingRight);
    }
 
}
