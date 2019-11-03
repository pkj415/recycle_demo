pragma solidity ^0.5.1;

import "./ERC223Mintable.sol";

/**
 * @dev Extension of {ERC223} that adds a set of accounts with the {MinterRole},
 * which have permission to mint (create) new tokens as they see fit.
 *
 * At construction, the deployer of the contract is the only minter.
 */
contract Recycle is ERC223Mintable {

   /**
     * @dev See {ERC20-_mint}.
     *
     * Requirements:
     *
     * - the caller must have the {MinterRole}.
     */
    function mint(address account, uint256 amount) public onlyMinter returns (bool) {
        _totalSupply.add(amount);
        balances[account].add(amount);
        return true;
    }

}
