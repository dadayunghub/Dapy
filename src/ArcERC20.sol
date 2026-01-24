// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;

import "@openzeppelin/contracts-upgradeable/token/ERC20/ERC20Upgradeable.sol";
import "@openzeppelin/contracts-upgradeable/token/ERC20/extensions/ERC20BurnableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/token/ERC20/extensions/ERC20PermitUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/token/ERC20/extensions/ERC20VotesUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import "@openzeppelin/contracts-upgradeable/utils/MulticallUpgradeable.sol";

contract ArcERC20 is
    Initializable,
    ERC20Upgradeable,
    ERC20BurnableUpgradeable,
    ERC20PermitUpgradeable,
    ERC20VotesUpgradeable,
    AccessControlUpgradeable,
    MulticallUpgradeable
{
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant PLATFORM_ROLE = keccak256("PLATFORM_ROLE");

    string public contractURI;
    address public primarySaleRecipient;
    address public platformFeeRecipient;
    uint96 public platformFeeBps;

    /// @custom:oz-upgrades-unsafe-allow constructor
    constructor() {
        _disableInitializers();
    }

    function initialize(
        string memory name_,
        string memory symbol_,
        address admin
    ) public initializer {
        __ERC20_init(name_, symbol_);
        __ERC20Burnable_init();
        __ERC20Permit_init(name_);
        __ERC20Votes_init();
        __AccessControl_init();
        __Multicall_init();

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(MINTER_ROLE, admin);
        _grantRole(PLATFORM_ROLE, admin);

        primarySaleRecipient = admin;
        platformFeeRecipient = admin;
        platformFeeBps = 500; // 5%
    }

    /* ───────────────── Minting ───────────────── */

    function mintTo(address to, uint256 amount)
        external
        onlyRole(MINTER_ROLE)
    {
        _mint(to, amount);
    }

    function mintWithSignature(
        address to,
        uint256 amount
    ) external onlyRole(MINTER_ROLE) {
        // Simplified placeholder
        // Arc/thirdweb usually verifies EIP-712 signatures here
        _mint(to, amount);
    }

    /* ───────────────── Metadata / Fees ───────────────── */

    function setContractURI(string memory _uri)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        contractURI = _uri;
    }

    function setPrimarySaleRecipient(address recipient)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        primarySaleRecipient = recipient;
    }

    function setPlatformFeeInfo(address recipient, uint96 bps)
        external
        onlyRole(PLATFORM_ROLE)
    {
        require(bps <= 10_000, "Invalid BPS");
        platformFeeRecipient = recipient;
        platformFeeBps = bps;
    }

    /* ───────────────── Overrides ───────────────── */

    function _update(
        address from,
        address to,
        uint256 value
    )
        internal
        override(ERC20Upgradeable, ERC20VotesUpgradeable)
    {
        super._update(from, to, value);
    }

    function nonces(address owner)
        public
        view
        override(ERC20PermitUpgradeable)
        returns (uint256)
    {
        return super.nonces(owner);
    }
}
