import { PushChain } from "@pushchain/core";
import { ethers } from "ethers";
import nodemailer from "nodemailer";
import fs from "fs";

// ENV
const encrypted = process.env.PRIVATE_KEY;
const PRIVATE_KEY = decryptAES256(encrypted, secret);
const secret = process.env.secret;
const CA_ADDRESS = process.env.CA_ADDRESS;
const TODO = process.env.TODO;
const recipients = JSON.parse(process.env.WALLETS || "[]");


const ERC20_ABI = JSON.parse(
  fs.readFileSync("./pusherc20abi.json", "utf-8") || "[]"
);


const transporter = nodemailer.createTransport({
  service: "gmail",
  auth: {
    user: process.env.EMAIL_USER,
    pass: process.env.EMAIL_APP_PASSWORD,
  },
});


function decryptAES256(encryptedText, secret) {
  const key = deriveKey(secret);
  
  const [ivBase64, encrypted] = encryptedText.split(":");
  const iv = Buffer.from(ivBase64, "base64");
  
  const decipher = crypto.createDecipheriv("aes-256-cbc", key, iv);
  let decrypted = decipher.update(encrypted, "base64", "utf8");
  decrypted += decipher.final("utf8");
  
  return decrypted;
}

async function main() {
  const results = [];

  const provider = new ethers.JsonRpcProvider(
    "https://sepolia.gateway.tenderly.co"
  );

  const wallet = new ethers.Wallet(PRIVATE_KEY, provider);

  const universalSigner =
    await PushChain.utils.signer.toUniversal(wallet);

  const pushClient = await PushChain.initialize(universalSigner, {
    network: PushChain.CONSTANTS.PUSH_NETWORK.TESTNET,
  });

  console.log("Sender:", wallet.address);

  // 🔹 NATIVE TRANSFER
  if (TODO === "transferpush") {
    const balance = await provider.getBalance(wallet.address);

    if (balance === 0n) {
      console.log("❌ No native balance.");
      return;
    }

    for (const recipient of recipients) {
      try {
        const txHash =
          await pushClient.universal.sendTransaction({
            to: recipient.address,
            value: BigInt(recipient.amount),
          });

        results.push({ address: recipient.address, status: "SUCCESS", txHash });

      } catch (error) {
        results.push({ address: recipient.address, status: "FAILED", error: error.message });
      }
    }
  }

  // 🔹 ERC20 TRANSFER
  if (TODO === "transfer") {
    if (!CA_ADDRESS) {
      throw new Error("CA_ADDRESS is required for ERC20 transfer");
    }

    const tokenContract = new ethers.Contract(
      CA_ADDRESS,
      ERC20_ABI,
      wallet
    );

    
    const decimals = await tokenContract.decimals();
  const tokenBalance = await tokenContract.balanceOf(wallet.address);

    console.log("Token Balance:", tokenBalance.toString());

    if (tokenBalance === 0n) {
      console.log("❌ No ERC20 token balance.");
      return;
    }

    for (const recipient of recipients) {
      try {
        
        const parsedAmount =
  PushChain.utils.helpers.parseUnits(
    recipient.amount.toString(),
    decimals
  );
        
        const data = PushChain.utils.helpers.encodeTxData({
  abi: ERC20_ABI,
  functionName: 'transfer',
  // Transfer 10 tokens, converted to 18 decimal places
  args: [recipient.address, parsedAmount],
});

        const txHash =
          await pushClient.universal.sendTransaction({
            to: CA_ADDRESS,
            value: BigInt('0'),
            data: data,
          });

        results.push({
  address: recipient.address,
  status: "SUCCESS",
  txHash: typeof txResponse === "string" ?
    txResponse :
    txResponse.hash || JSON.stringify(txResponse)
});

      } catch (error) {
        results.push({ address: recipient.address, status: "FAILED", error: error.message });
      }
    }
  }
await sendEmail(results);
  console.log(results);
}

async function sendEmail(results) {
  const report = results
    .map((r) => JSON.stringify(r))
    .join("\n");

  await transporter.sendMail({
    from: process.env.EMAIL_USER,
    to: process.env.RECEIVER_EMAIL,
    subject: "Push Chain Execution Report",
    text: report,
  });

  console.log("📧 Email report sent.");
}


main().catch(console.error);
