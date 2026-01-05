export default async function handler(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ message: "Method not allowed" });
  }

  const { wallet, ref } = req.body;

  // Example referral map
  const referralLinks = {
    Airdrop: "https://t.me/Meta_TokenAirdrop?text=Hello%20there!%20Wallet:%20{wallet}%20Applying%20for%20Airdrop",
     };

  // Default fallback link
  const defaultLink = "https://t.me/Meta_TokenAirdrop?text=Hello%20there!%20Wallet:%20{wallet}%20Applying%20for%20Airdrop";
   
  // Select link template
  const template = referralLinks[ref] || defaultLink;

  // Replace placeholders
  const finalLink = template
    .replace("{wallet}", encodeURIComponent(wallet));
    
  return res.status(200).json({ telegramLink: finalLink });
}
