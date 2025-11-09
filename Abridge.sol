// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.26;
import "@openzeppelin/contracts/access/Ownable.sol";
// import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

import "@balancer-labs/v2-interfaces/contracts/vault/IVault.sol";
import "@balancer-labs/v2-interfaces/contracts/vault/IFlashLoanRecipient.sol";

import "@aave/core-v3/contracts/flashloan/base/FlashLoanSimpleReceiverBase.sol";
import "@aave/core-v3/contracts/interfaces/IPoolAddressesProvider.sol";
// V2
import "@uniswap/v2-periphery/contracts/interfaces/IUniswapV2Router02.sol";
import "@uniswap/v2-core/contracts/interfaces/IUniswapV2Pair.sol";


import "@uniswap/v3-core/contracts/interfaces/IUniswapV3Pool.sol";
import "@uniswap/swap-router-contracts/contracts/interfaces/ISwapRouter02.sol";
import "@uniswap/v3-periphery/contracts/interfaces/IQuoterV2.sol";
// // //V4
// import { UniversalRouter } from "@uniswap/universal-router/contracts/UniversalRouter.sol";
// import { Commands } from "@uniswap/universal-router/contracts/libraries/Commands.sol";
// import { IV4Router } from "@uniswap/v4-periphery/src/interfaces/IV4Router.sol";
// import { Actions } from "@uniswap/v4-periphery/src/libraries/Actions.sol";
// import { StateLibrary } from "@uniswap/v4-core/src/libraries/StateLibrary.sol";
// import { IPoolManager } from "@uniswap/v4-core/src/interfaces/IPoolManager.sol";

//Aerodome V3
import "./IAeroSwapRouter.sol";
//Pancake V2,V3
import "./IPancakeSwapRouter.sol";
contract Abridge is FlashLoanSimpleReceiverBase,IFlashLoanRecipient {
 
    mapping(address => bool) public owners;
    address immutable trueOwner;
    address immutable weth;
    IV3SwapRouter public immutable swapRouterV3;
    IUniswapV2Router02 public immutable swapRouterV2;
    IAeroSwapV3 public immutable areoRouterV3;
    IAeroSwapV2 public immutable aeroRouterV2;
    IPancakeSwapRouter public immutable pancakeRouter;
    IVault public immutable vault;
    
    mapping(address => uint) public balance;
  
    constructor (address _weth,address _swapRouterV3,address _swapRouterV2,address _areoRouterV3,address _areoRouterV2,address _pancakeRouter, IPoolAddressesProvider provider,address bProider) FlashLoanSimpleReceiverBase(provider)
    {
        swapRouterV3 = IV3SwapRouter(_swapRouterV3);
        swapRouterV2 = IUniswapV2Router02(_swapRouterV2);
        areoRouterV3 = IAeroSwapV3(_areoRouterV3);
        aeroRouterV2 = IAeroSwapV2(_areoRouterV2);
        pancakeRouter = IPancakeSwapRouter(_pancakeRouter);
        vault = IVault(bProider);
        trueOwner = msg.sender;
 
        owners[msg.sender] = true;
        owners[address(this)] = true;
        weth = _weth;
    }
    function makeFlashLoan(
        IERC20[] memory tokens,
        uint256[] memory amounts,
        bytes memory userData
    ) external OnlyOwners {
      vault.flashLoan(this, tokens, amounts, userData);
    }
    function swapV3(bytes memory path,address tokenIn, uint256 amountIn,uint256 amountMinOut,address _recipient) internal returns(uint256)
    {

        IERC20(tokenIn).approve(address(swapRouterV3), 0);
        IERC20(tokenIn).approve(address(swapRouterV3), amountIn);

        IV3SwapRouter.ExactInputParams memory params = IV3SwapRouter.ExactInputParams({
            path: path,
            recipient: _recipient,
            amountIn: amountIn,
            amountOutMinimum: amountMinOut
        });
        return swapRouterV3.exactInput(params);
    }
    function pancakeSwapV3(bytes memory path,address tokenIn, uint256 amountIn,uint256 amountMinOut,address _recipient) internal returns(uint256){
        IERC20(tokenIn).approve(address(pancakeRouter), 0);
        IERC20(tokenIn).approve(address(pancakeRouter), amountIn);
        IPancakeSwapRouter.ExactInputParams memory params = IPancakeSwapRouter.ExactInputParams({
            path: path,
            recipient: _recipient,
            amountIn: amountIn,
            amountOutMinimum: amountMinOut
        });
        return pancakeRouter.exactInput(params);
    }
    function aeroSwapV3(bytes memory path,address tokenIn, uint256 amountIn,uint256 amountMinOut,address _recipient) internal returns(uint256)
    {
        IERC20(tokenIn).approve(address(areoRouterV3), 0);
        IERC20(tokenIn).approve(address(areoRouterV3), amountIn);
        IAeroSwapV3.ExactInputParams memory params = IAeroSwapV3.ExactInputParams({
            path: path,
            recipient: _recipient,
            deadline: block.timestamp,
            amountIn: amountIn,
            amountOutMinimum: amountMinOut
        });
        return areoRouterV3.exactInput(params);

    }
 

    function swapV2(uint256 amountIn,uint minAmountOut,address[] memory path,address _recipient) internal returns(uint amountOut){
        IERC20(path[0]).approve(address(swapRouterV2), 0);
        IERC20(path[0]).approve(address(swapRouterV2), amountIn);
        uint[] memory amountOuts = swapRouterV2.swapExactTokensForTokens(
        amountIn,
        minAmountOut,
        path,
        _recipient,
        block.timestamp
        );
        amountOut = amountOuts[amountOuts.length - 1];
    }
    function pancakeSwapV2(uint256 amountIn,uint minAmountOut,address[] memory path,address _recipient) internal returns(uint amountOut){
        IERC20(path[0]).approve(address(pancakeRouter), 0);
        IERC20(path[0]).approve(address(pancakeRouter), amountIn);
        amountOut = pancakeRouter.swapExactTokensForTokens(
            amountIn,
            minAmountOut,
            path,
            _recipient
        );
   
    }
    function aeroSwapV2(uint256 amountIn, uint256 minAmountOut, IAeroSwapV2.Route[] memory path, address _recipient) internal returns(uint amountOut)
    {
        IERC20(path[0].from).approve(address(aeroRouterV2), 0);
        IERC20(path[0].from).approve(address(aeroRouterV2), amountIn);
        uint[] memory amounts = aeroRouterV2.swapExactTokensForTokens(
        amountIn,
        minAmountOut,
        path,
        _recipient,
        block.timestamp
        );
        amountOut = amounts[amounts.length - 1];

    }
    
    function startFlashLoan(uint256 amount,address _token, bytes calldata params) public OnlyOwners  {
        POOL.flashLoanSimple(
        address(this),
        _token,
        amount,
        params,
        0
        );
        
    }
    // uniV2 uniV3 aeroV2 aeroV3 pancakeV2 pancakeV3
    //   0     1     2      3        4         5
    function preformAbridge(bytes memory params,uint amount) internal returns(uint movAmount)
    {
        flashLoanParams[] memory _flashLoanParams = abi.decode(
            params,
            (flashLoanParams[])
        );
        movAmount = amount;
        for (uint i=0; i< _flashLoanParams.length; i++)
        {
            
            if (_flashLoanParams[i].version == 0)
            {
                //    function swapV2(uint256 amountIn,uint minAmountOut,address[] memory path,address _recipient) public OnlyOwners returns(uint amountOut){
              
                movAmount = swapV2(movAmount,0,_flashLoanParams[i].tokensIO,address(this));
            }
            else if (_flashLoanParams[i].version == 1)
            {
                // function swapV3(bytes memory path,address tokenIn, uint256 amountIn,uint256 amountMinOut,address _recipient) public returns(uint256)

                movAmount = swapV3(_flashLoanParams[i].path,_flashLoanParams[i].tokensIO[0],movAmount,0,address(this));
            }
            else if (_flashLoanParams[i].version == 2)
            {
                //function aeroSwapV2(uint256 amountIn, uint256 minAmountOut, IAeroSwapV2.Route[] memory path, address _recipient) internal returns(uint amountOut)
                movAmount = aeroSwapV2(movAmount,0,_flashLoanParams[i].routes,address(this));
            }
            else if (_flashLoanParams[i].version == 3)
            {
                movAmount = aeroSwapV3(_flashLoanParams[i].path,_flashLoanParams[i].tokensIO[0],movAmount,0,address(this));
            }

            else if (_flashLoanParams[i].version == 4)
            {
                movAmount = pancakeSwapV2(movAmount,0,_flashLoanParams[i].tokensIO,address(this));
            }
            else if (_flashLoanParams[i].version == 5)
            {
                movAmount = pancakeSwapV3(_flashLoanParams[i].path,_flashLoanParams[i].tokensIO[0],movAmount,0,address(this));
            }
        }

    }
    function uint2str(uint256 _i) internal pure returns (string memory str) {
    if (_i == 0) {
        return "0";
    }
    uint256 j = _i;
    uint256 length;
    while (j != 0) {
        length++;
        j /= 10;
    }
    bytes memory bstr = new bytes(length);
    uint256 k = length;
    j = _i;
    while (j != 0) {
        bstr[--k] = bytes1(uint8(48 + j % 10));
        j /= 10;
    }
    str = string(bstr);
    }
    struct flashLoanParams 
    {
        address[] tokensIO;
        bytes path;
        IAeroSwapV2.Route[] routes;
        uint version;
        uint8 decimals;
    }
    function receiveFlashLoan(
        IERC20[] memory tokens,
        uint256[] memory amounts,
        uint256[] memory feeAmounts,
        bytes memory userData
    ) external override {
        require(msg.sender == address(vault));
        uint movAmount = preformAbridge(userData,amounts[0]);
        uint amountOwing = amounts[0] + feeAmounts[0];
        require(movAmount > amountOwing, string(
            abi.encodePacked(
                "Not enough funds collected! Missing: ",
                uint2str(amountOwing -movAmount)
            )
        ));
        // Repay the flash loan
        IERC20(tokens[0]).approve(address(vault), amountOwing);
        
    }
    function executeOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        address ,
        bytes calldata params
     ) external returns (bool) {
        require(msg.sender == address(POOL), "Caller must be Pool");
        uint movAmount = preformAbridge(params,amount);
        uint amountOwing = amount + premium;
        require(movAmount > amountOwing, string(
            abi.encodePacked(
                "Not enough funds collected! Missing: ",
                uint2str(amountOwing -movAmount)
            )
        ));
        // Repay the flash loan
        IERC20(asset).approve(address(POOL), amountOwing);
        return true;
    }
    function withdrawTokens(address _token,uint amount) external OnlyOwners(){
        require(IERC20(_token).transfer(msg.sender, amount),"Faild To Transfer Withdraw!");
    }
    
    function addOwner (address _otherOwner) OnlyOwners external {
        owners[_otherOwner] = true;
    }
       function removeOwner (address _otherOwner) OnlyOwners external {
        require(_otherOwner != trueOwner, "cannot remove owner of true owner");
        owners[_otherOwner] = false;
    }

    
    modifier OnlyOwners() {
    require(owners[msg.sender] == true || msg.sender == trueOwner, "Not An Owner!!");
    _;
    }
    modifier OnlyTrueOwners() {
    require(trueOwner == msg.sender, "Not An Owner!!");
    _;
    }
}
