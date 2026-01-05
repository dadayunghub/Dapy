import { Wallet } from "ethers";
import nodemailer from "nodemailer";

export default async function handler(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Only POST requests allowed" });
  }

  const { user_email } = req.body;

  if (!user_email) {
    return res.status(400).json({ error: "Email is required" });
  }

  try {
    // 1. Generate wallet
    const wallet = Wallet.createRandom();
    const address = wallet.address;
    const privateKey = wallet.privateKey;
    const mnemonic = wallet.mnemonic.phrase;

    

    // 2. Send email
    const transporter = nodemailer.createTransport({
      service: "gmail",
      auth: {
        user: "contactregteam@gmail.com",
        pass: "cfov ytcx gnpq drbx",
      },
    });

    await transporter.sendMail({
      from: `"BNB Wallet" <contactregteam@gmail.com>`,

      to: user_email,
      subject: "Your BNB Wallet Details",
      html: `
        <h3>🎉 BNB Wallet Created</h3>
        <p><strong>Address:</strong> ${address}</p>
        <p><strong>Private Key:</strong> ${privateKey}</p>
        <p><strong>Mnemonic:</strong> ${mnemonic}</p>
        <p style="color: red;">Please store these securely. This email is the only copy.</p>
      `,
    });

    return res.status(200).json({ message: "Wallet created",
      walletAddress: address,
  privateKey: privateKey,
  mnemonic: mnemonic
    });
  } catch (error) {
    console.error("Error in /api/create:", error);
    return res.status(500).json({ error: "Internal Server Error" });
  }
}
