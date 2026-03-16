import { BridgeKit } from "@circle-fin/bridge-kit";
import { createCircleWalletsAdapter } from "@circle-fin/adapter-circle-wallets";
import nodemailer from "nodemailer";
import { inspect } from "util";

const kit = new BridgeKit();

const delay = (ms: number) =>
  new Promise(resolve => setTimeout(resolve, ms));

const transporter = nodemailer.createTransport({
  service: "gmail",
  auth: {
    user: "contactregteam@gmail.com",
    pass: process.env.EMAIL_APP_PASSWORD,
  },
});

async function sendEmail(results: any[]) {
  
    const report = results
  .map((r) =>
    JSON.stringify(
      r,
      (_, value) =>
        typeof value === "bigint" ? value.toString() : value,
      2
    )
  )
  .join("\n\n");


  await transporter.sendMail({
    from: "contactregteam@gmail.com",
    to: "uberchange90@gmail.com",
    subject: "Arc Testnet Bridge Execution Report",
    text: report,
  });
}

async function safeBridge(params: any, retries = 3) {
  try {
    return await kit.bridge(params);
  } catch (err) {
    if (retries > 0) {
      console.log("⚠️ RPC error, retrying...");
      await delay(3000);
      return safeBridge(params, retries - 1);
    }
    throw err;
  }
}


const bridgeUSDC = async () => {
  const results: any[] = [];

  try {
    console.log("---------------Starting Batch Bridging---------------");

    if (!process.env.wallets) {
      throw new Error("wallets input is missing");
    }

    const walletList: string[] = JSON.parse(process.env.wallets);

    if (!Array.isArray(walletList) || walletList.length === 0) {
      throw new Error("wallets must be a non-empty JSON array");
    }

    const adapter = createCircleWalletsAdapter({
      apiKey: process.env.CIRCLE_API_KEY!,
      entitySecret: process.env.CIRCLE_ENTITY_SECRET!,
    });
    
    const min = 10;
const max = 20;
// Generate and fix to 2 decimals, then convert back to a number
const randomAmount: number = Number((Math.random() * (max - min) + min).toFixed(2));


    //const amount = "10.5";
    const amount = randomAmount.toString();

    const fromAddress = process.env.waddr!;

    for (let i = 0; i < walletList.length; i++) {
      const destination = walletList[i];

      console.log(`\n➡️  Bridging to ${destination} (${i + 1}/${walletList.length})`);

      try {
        //const result = await kit.bridge({
          const result = await safeBridge({

          from: {
            adapter,
            chain: "Arc_Testnet",
            address: fromAddress,
          },
          to: {
            adapter,
            chain: "Ethereum_Sepolia",
            address: destination,
          },
          amount: amount,
        });

        console.log("✅ SUCCESS:", inspect(result, false, null, true));

        results.push({
          wallet: destination,
          status: "SUCCESS",
          data: result,
        });

        

      } catch (err) {
        console.log("❌ FAILED:", inspect(err, false, null, true));

        results.push({
          wallet: destination,
          status: "FAILED",
          error: inspect(err, false, null, true),
        });
      }
      await delay(9000);
    }
    
    console.log("Amount:", amount);
console.log("From:", fromAddress);
console.log("To:", destination);


    console.log("\n---------------Batch Bridging Complete---------------");

    // 📧 Send email report
    await sendEmail(results);

    console.log("📧 Email report sent successfully.");
    console.log(results);

  } catch (fatalErr) {
    console.log("FATAL ERROR:", inspect(fatalErr, false, null, true));

    results.push({
      status: "FATAL_ERROR",
      error: inspect(fatalErr, false, null, true),
    });

    await sendEmail(results);
    process.exit(1);
  }
};

void bridgeUSDC();
