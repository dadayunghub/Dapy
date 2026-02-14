import { PushChain } from '@pushchain/core';
import { ethers } from 'ethers';
import recipients from './recipients.json'
assert { type: 'json' };

const balance = await provider.getBalance(wallet.address);
console.log("Balance:", balance.toString());


async function main() {
  // 1️⃣ Connect to provider (Push Testnet RPC)
  const provider = new ethers.JsonRpcProvider(
    "https://sepolia.gateway.tenderly.co"
  );
  
  // 2️⃣ Create wallet from PRIVATE KEY
  const wallet = new ethers.Wallet(process.env.PRIVATE_KEY, provider);
  
  console.log("Sender:", wallet.address);
  
  // 3️⃣ Convert to Universal Signer
  const universalSigner =
    await PushChain.utils.signer.toUniversal(wallet);
  
  // 4️⃣ Initialize PushChain Client
  const pushChainClient = await PushChain.initialize(universalSigner, {
    network: PushChain.CONSTANTS.PUSH_NETWORK.TESTNET,
  });
  
  console.log(
    "Universal Account:",
    pushChainClient.universal.account.address
  );
  
  // 5️⃣ Loop through recipients
  for (const recipient of recipients) {
    try {
      console.log(`Sending to ${recipient.address}`);
      
      const txHash =
        await pushChainClient.universal.sendTransaction({
          to: recipient.address,
          value: BigInt(recipient.amount),
        });
      
      console.log("✅ Sent:", txHash);
    } catch (error) {
      console.error("❌ Failed:", recipient.address, error.message);
    }
  }
}

main();