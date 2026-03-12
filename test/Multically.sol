// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract Multicall {

    struct Call {
        address target;
        bytes callData;
    }

    struct Result {
        bool success;
        bytes returnData;
    }

    /**
     * @notice Execute multiple calls in a single request
     * @param calls array of call objects
     * @return blockNumber current block number
     * @return results array of results
     */
    function aggregate(Call[] calldata calls)
        external
        view
        returns (uint256 blockNumber, Result[] memory results)
    {
        blockNumber = block.number;
        results = new Result[](calls.length);

        for (uint256 i = 0; i < calls.length; i++) {

            (bool success, bytes memory data) =
                calls[i].target.staticcall(calls[i].callData);

            results[i] = Result({
                success: success,
                returnData: data
            });
        }
    }

    /**
     * @notice Same as aggregate but returns only returnData
     */
    function tryAggregate(Call[] calldata calls)
        external
        view
        returns (bytes[] memory returnData)
    {
        returnData = new bytes[](calls.length);

        for (uint256 i = 0; i < calls.length; i++) {

            (bool success, bytes memory data) =
                calls[i].target.staticcall(calls[i].callData);

            require(success, "Multicall: call failed");

            returnData[i] = data;
        }
    }

    /**
     * @notice Helper to get block number
     */
    function getBlockNumber() external view returns (uint256) {
        return block.number;
    }

    /**
     * @notice Helper to get block timestamp
     */
    function getBlockTimestamp() external view returns (uint256) {
        return block.timestamp;
    }
}
