require('dotenv').config();
const { ethers, parseEther } = require("ethers");
const fs = require("fs");
const {Simulator,Pool} = require("./helpers/pool-eval.js")


let provider = new ethers.JsonRpcProvider(process.env.RPC_URL);
let wsProvider = new ethers.WebSocketProvider(process.env.RPC_WS)
const wallet = new ethers.Wallet(process.env.PRIVATE_KEY, provider);


const weth = "0x4200000000000000000000000000000000000006"
const usdc = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"



const artifact = JSON.parse(
  fs.readFileSync("./Abridge.json", "utf8")
);

const ABI = artifact.abi;

async function abridgeSwapper(swapParams) {


  console.log(swapParams)
  const amountIn = swapParams.amountIn;
  const abridger = new ethers.Contract("0x5b05De2cF3D1EA1e50D822b8921f64CCd503F59F", ABI, wallet);

  const coder = new ethers.AbiCoder();
  const encodedParams = coder.encode(
    ["tuple(address[] tokensIO, bytes path, tuple(address from,address to,bool stable,address factory)[] routes, uint256 version,uint8 decimals)[]"],
    [swapParams.params]
  );

  try {
    console.log("token in", swapParams.params[0].tokensIO[0])

    const tx = await abridger.makeFlashLoan([swapParams.params[0].tokensIO[0]], [amountIn], encodedParams);

    console.log(`Transaction submitted: ${tx.hash}`);

    const receipt = await tx.wait();
    console.log(`Transaction confirmed in block ${receipt.blockNumber}`);
    console.log(`-------------------------------------------------------------------------\nABRIDGE COMPLETE\n-------------------------------------------------------------------------`)
  } catch (err) {
    console.error('Swap failed:', err);
  }

}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
function colorDiff(diff) {
  if (diff >= 0) {
    // Green bold
    return `\x1b[1m\x1b[32m+${diff}%\x1b[0m`;
  } else {
    // Red bold
    return `\x1b[1m\x1b[31m${diff}%\x1b[0m`;
  }
}
  async function reconnect() {
    console.log("Reconnecting...");
    // wait a bit
    await new Promise(r => setTimeout(r, 2000));
    // recreate provider
    wsProvider = new ethers.WebSocketProvider(process.env.RPC_WS)

    // reattach events if needed
    console.log("Reconnected!");
}

async function swap_brain(brainParams) {
  const sim = new Simulator(provider);
  console.log("Amount In:",parseEther(brainParams.tokens[0].amountIn.toString()))
  let pools = [];
  for (let i=0; i< brainParams.tokens.length;i++)
  {
    for (let x=0; x<brainParams.tokens[i].pools.length;x++)
    {
      pools.push(new Pool(brainParams.tokens[i].token,
        brainParams.tokens[i].pools[x].pool,
        brainParams.tokens[i].amountIn,
        brainParams.tokens[i].pools[x].decimalsIn,
        brainParams.tokens[i].pools[x].decimalsOut,
        brainParams.tokens[i].pools[x].version,wsProvider))
    }
  

  }



  const nowSeconds = Math.floor(Date.now());
  console.log(wsProvider.websocket ? "Using WebSocket ✅" : "Not using WebSocket ❌");

  
  for (let i = 0; i < pools.length; i++) {
   if (pools[i].initalized == false)
    {
    await pools[i].InitPool();
    console.log("initialize pool")
    }
  }
  console.log(pools[0].pool,"first pool")
   for (let i = 0; i < pools.length; i++) {
    try {

        if (pools[i].version === 0) {
          
            pools[i].poolContract.on(
                "Swap",
                async (sender, amount0In, amount1In, amount0Out, amount1Out, to, event) => {
                    pools[i].reserves = pools[i].updateReservesV2(
                        pools[i].reserves,
                        amount0In - amount0Out,
                        amount1In - amount1Out
                    );
                    console.log(`\x1b[35mVersion ${pools[i].version} Triggered\x1b[0m`)
               
                    const slippages = sim.getAbridges(pools[i].pool, pools);
                    
                    await logicalAbridge(slippages);
                }
            );
        } else if (pools[i].version == 2) {
            // FIX UPDATE V2
            pools[i].poolContract.on(
                "Swap",
                async (sender, to, amount0In, amount1In, amount0Out, amount1Out, event) => {
                    pools[i].reserves = pools[i].updateReservesV2(
                        pools[i].reserves,
                        amount0In - amount0Out,
                        amount1In - amount1Out
                    );
                    console.log(`\x1b[35mVersion ${pools[i].version} Triggered\x1b[0m`)
                    const slippages = sim.getAbridges(pools[i].pool, pools);
                    
                    await logicalAbridge(slippages);
                }
            );
        } else {
            pools[i].poolContract.on(
                "Swap",
                async (sender, recipient, amount0, amount1, sqrtPriceX96, liquidity, tick, event) => {
                    pools[i].reserves = pools[i].updateReservesV3(
                        sqrtPriceX96,
                        liquidity,
                        amount0,
                        amount1
                    );
                    console.log(`\x1b[35mVersion ${pools[i].version} Triggered\x1b[0m`)
                    const slippages = sim.getAbridges(pools[i].pool, pools);
                    
                    await logicalAbridge(slippages);
                }
            );
        }
    } catch (err) {
        console.log(err);
    }
}

    const laterSeconds = Math.floor(Date.now());
    console.log(`Delay: ${laterSeconds - nowSeconds}ms`)



    async function logicalAbridge(slippages) {
      if (slippages.length < 1) {
        console.log("0 slippages")
        return;
      }

      slippages.sort((a, b) => parseFloat(b.slippage) - parseFloat(a.slippage));
      for (let i = 0; i < slippages.length; i++) {
        console.log(`\x1b[96m[${slippages[i].poolType[0]}->${slippages[i].poolType[1]}]\x1b[0m \x1b[1m\x1b[95mProfit: ${colorDiff(((parseFloat(slippages[i].slippage) - 1) * 100).toFixed(3))}`);
      }
      console.log(`\n`)
      let profit = (parseFloat(slippages[0].slippage) - 1) * 100
      function replacer(key, value) {
        if (value && value._isBigNumber) return value.toString();
        return value;
      }
      // 
      if (profit >= 0.05) {
        // if (!swapped){
        swapped = true;
        const swapParams =
        {
          params: slippages[0].params,
          amountIn: parseEther(brainParams.tokens[0].amountIn.toString())
        }

        console.log(JSON.stringify(slippages[0].params, replacer, 2));
        await abridgeSwapper(swapParams)


      }
    }

    wsProvider.websocket.on("close", async (code) => {
      console.log(`WebSocket closed with code: ${code}`);

      // your reconnect logic
      await reconnect();
      swap_brain(brainParams)
    });


  }

var swapped = false;
// uniV2 uniV3 aeroV2 aeroV3 pancakeV2 pancakeV3
//   0     1     2      3        4         5

swap_brain({
  tokens: [
    {
      token: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", // KTA
      amountIn: process.argv[2], //edit in real trnsx
      pools: [
        {
          pool: "0x6c561B446416E1A00E8E93E221854d6eA4171372",
          fee: 10000n,
          version: 1,
          decimalsIn: 18,
          decimalsOut: 6,
        },
        {
          pool: "0x88A43bbDF9D098eEC7bCEda4e2494615dfD9bB9C",
          fee: 2500n,
          decimalsIn:18,
          version: 0,
          decimalsOut: 6,
        },
        //  {
        //   pool: "0x5aa4AD647580bfE86258d300Bc9852F4434E2c61",
        //   fee: 3000n,
        //   decimalsIn:18,
        //   version: 1,
        //   decimalsOut: 18,
        // },
      
      ],
    },
  ],
});
//FIX CONTRACT WITH DECIMALS ERROR
  //{
      //   token: "0x1bc0c42215582d5A085795f4baDbaC3ff36d1Bcb", //KTA
      //   amountIn: 0.5,

      //   pools: [{
      //     pool: "0xC1a6FBeDAe68E1472DbB91FE29B51F7a0Bd44F97",
      //     fee: 10000n,
      //     version: 1,
      //     decimals: 18, // for decimlas swapping returns the amount out in the out tokens decimals then just reformat to 18 decimals after
      //   },{
      //     pool: "0x75fb62AA7d072a6A96692B207278A760E5df42CC",
      //     fee: 3000n,
      //     version: 1,
      //     decimals: 18, // for decimlas swapping returns the amount out in the out tokens decimals then just reformat to 18 decimals after
      //   },
      //   {
      //     pool: "0xd23FE2DB317e1A96454a2D1c7e8fc0DbF19BB000",
      //     fee: 200n,
      //     version: 3,
      //     decimals: 18,
      //   },

      //   ]
      // },

 
//0x940181a94A35A4569E4529A3CDfB74e38FD98631
