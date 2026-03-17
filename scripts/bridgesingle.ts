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

async function sendEmail(result: any) {
  const report = JSON.stringify(
    result,
    (_, value) => (typeof value === "bigint" ? value.toString() : value),
    2
  );

  await transporter.sendMail({
    from: "contactregteam@gmail.com",
    to: "uberchange90@gmail.com",
    subject: "Arc Testnet Bridge Execution Report",
    text: report,
  });
}

async function safeBridge(params: any, retries = 3): Promise<any> {
  try {
    return await kit.bridge(params);
  } catch (err) {
    if (retries > 0) {
      console.log(`⚠️ RPC error, retrying... (${retries} left)`);
      await delay(3000);
      return safeBridge(params, retries - 1);
    }
    throw err;
  }
}

const bridgeUSDC = async () => {
  let result: any = {};

  try {
    console.log("---------------Starting Single Bridge---------------");

    const adapter = createCircleWalletsAdapter({
      apiKey: process.env.CIRCLE_API_KEY!,
      entitySecret: process.env.CIRCLE_ENTITY_SECRET!,
    });

    // Random amount
    const min = 10;
    const max = 20;
    const amount = Number(
      (Math.random() * (max - min) + min).toFixed(2)
    ).toString();

    const fromAddress = "0x758dca35b6d8158f8d1fa65c59a7c8f570dc7014";
    const destination = "0xCFC4dc7AE2C095f4da8B6D4c8c88Bed2303FB459"; // 👈 single wallet here

    if (!destination) {
      throw new Error("Destination wallet is missing");
    }

    console.log(`➡️ Bridging to ${destination}`);
    console.log("Amount:", amount);
    console.log("From:", fromAddress);

    const bridgeResult = await safeBridge({
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
      amount,
    });

    console.log("✅ SUCCESS:", inspect(bridgeResult, false, null, true));

    result = {
      wallet: destination,
      status: "SUCCESS",
      amount,
      data: bridgeResult,
    };

    console.log("\n---------------Bridge Complete---------------");

    await sendEmail(result);
    console.log("📧 Email sent");

  } catch (err) {
    console.log("❌ FAILED:", inspect(err, false, null, true));

    result = {
      status: "FAILED",
      error: inspect(err, false, null, true),
    };

    await sendEmail(result);
    process.exit(1);
  }
};

void bridgeUSDC();
