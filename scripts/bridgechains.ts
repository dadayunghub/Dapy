import { createEthersAdapterFromPrivateKey } from "@circle-fin/adapter-ethers-v6";
import { EthereumSepolia, ArcTestnet } from "@circle-fin/bridge-kit/chains";
import nodemailer from "nodemailer";
import { JsonRpcProvider } from "ethers";

// Map RPC endpoints by chain name
const RPC_BY_CHAIN_NAME: Record < string, string > = {
  [EthereumSepolia.name]: `https://eth-sepolia.g.alchemy.com/v2/${process.env.ALCHEMY_KEY}`,
  [ArcTestnet.name]: `https://arc-testnet.g.alchemy.com/v2/${process.env.ALCHEMY_KEY}`,
};

// Create an adapter
const adapter = createEthersAdapterFromPrivateKey({
  privateKey: process.env.PRIVATE_KEY as string,
  // Replace the default connection
  getProvider: ({ chain }) => {
    const rpcUrl = RPC_BY_CHAIN_NAME[chain.name];
    if (!rpcUrl) {
      throw new Error(`No RPC configured for chain: ${chain.name}`);
    }
    return new JsonRpcProvider(rpcUrl);
  },
});

const adapter = createCircleWalletsAdapter({
  apiKey: process.env.CIRCLE_API_KEY!,
  entitySecret: process.env.CIRCLE_ENTITY_SECRET!,
});