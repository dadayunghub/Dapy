import { TwitterApi } from 'twitter-api-v2';
import admin from 'firebase-admin';
import fs from 'fs';
import axios from 'axios';

const tweetVersions = [
  `Claim your $30 now! Just apply below 👇 bit.ly/Airdropss If you’re eligible, you’ll receive $30 in rewards! $GASS $WHITE $ZEUS $PEPE $HOLD @TrustWallet @MetaMask @trustwallet_th @trustwallet_ru @LeTrustWalletFR`,

  `Get rewarded with $30! 🤑 Apply here 👇 bit.ly/Airdropss Eligible users will be awarded $30. Don’t miss out! $GASS $WHITE $ZEUS $PEPE $HOLD @TrustWallet @MetaMask @trustwallet_th @trustwallet_ru @LeTrustWalletFR`,

  `🚨 Free $30 alert! Click below to apply 👇 bit.ly/Airdropss If eligible, you’ll receive a $30 reward instantly. $GASS $WHITE $ZEUS $PEPE $HOLD @TrustWallet @MetaMask @trustwallet_th @trustwallet_ru @LeTrustWalletFR`,

  `Want $30? It’s easy! Apply now 👇 bit.ly/Airdropss If you qualify, you’ll be awarded $30. $GASS $WHITE $ZEUS $PEPE $HOLD @TrustWallet @MetaMask @trustwallet_th @trustwallet_ru @LeTrustWalletFR`,

  `Eligible users can receive $30! Apply today 👇 bit.ly/Airdropss Don’t miss your chance! $GASS $WHITE $ZEUS $PEPE $HOLD @TrustWallet @MetaMask @trustwallet_th @trustwallet_ru @LeTrustWalletFR`,

  `🎉 Get $30 for participating! Apply here 👇 bit.ly/Airdropss Eligible users will receive the reward. $GASS $WHITE $ZEUS $PEPE $HOLD @TrustWallet @MetaMask @trustwallet_th @trustwallet_ru @LeTrustWalletFR`,

  `Airdrop live now! 💸 $30 reward for eligible users. Apply 👇 bit.ly/Airdropss Tag friends! $GASS $WHITE $ZEUS $PEPE $HOLD @TrustWallet @MetaMask @trustwallet_th @trustwallet_ru @LeTrustWalletFR`,

  `Here’s your chance to earn $30 🔥 Just apply using the link 👇 bit.ly/Airdropss You may be eligible for an airdrop! $GASS $WHITE $ZEUS $PEPE $HOLD @TrustWallet @MetaMask @trustwallet_th @trustwallet_ru @LeTrustWalletFR`,

  `🪂 Claim your free $30! Apply below 👇 bit.ly/Airdropss Eligibility applies. Good luck! $GASS $WHITE $ZEUS $PEPE $HOLD @TrustWallet @MetaMask @trustwallet_th @trustwallet_ru @LeTrustWalletFR`,

  `Don't miss this airdrop! Get $30 if eligible — just apply 👇 bit.ly/Airdropss Easy and fast. $GASS $WHITE $ZEUS $PEPE $HOLD @TrustWallet @MetaMask @trustwallet_th @trustwallet_ru @LeTrustWalletFR`,

  `🎁 Earn $30 just for applying! Hit the link 👇 bit.ly/Airdropss Rewards for eligible users. $GASS $WHITE $ZEUS $PEPE $HOLD @TrustWallet @MetaMask @trustwallet_th @trustwallet_ru @LeTrustWalletFR`,

  `💰 Want $30 for free? Apply now 👇 bit.ly/Airdropss If you’re eligible, you’ll receive the reward! $GASS $WHITE $ZEUS $PEPE $HOLD @TrustWallet @MetaMask @trustwallet_th @trustwallet_ru @LeTrustWalletFR`,

  `Apply today and earn $30! 💸 Click below 👇 bit.ly/Airdropss Only for eligible users. Don’t wait! $GASS $WHITE $ZEUS $PEPE $HOLD @TrustWallet @MetaMask @trustwallet_th @trustwallet_ru @LeTrustWalletFR`,

  `🔥 Airdrop time! Get $30 if eligible — apply now 👇 bit.ly/Airdropss Fast and simple. $GASS $WHITE $ZEUS $PEPE $HOLD @TrustWallet @MetaMask @trustwallet_th @trustwallet_ru @LeTrustWalletFR`,

  `Claim $30 in rewards! ✅ Just apply 👇 bit.ly/Airdropss Limited time offer for eligible users. $GASS $WHITE $ZEUS $PEPE $HOLD @TrustWallet @MetaMask @trustwallet_th @trustwallet_ru @LeTrustWalletFR`,

  `You could be eligible for $30! 💵 Apply here 👇 bit.ly/Airdropss Fast, free, and easy. $GASS $WHITE $ZEUS $PEPE $HOLD @TrustWallet @MetaMask @trustwallet_th @trustwallet_ru @LeTrustWalletFR`,

  `🤑 Free $30? Yes please! Apply below 👇 bit.ly/Airdropss Reward for those who qualify. Don’t miss it! $GASS $WHITE $ZEUS $PEPE $HOLD @TrustWallet @MetaMask @trustwallet_th @trustwallet_ru @LeTrustWalletFR`,

  `🚀 Grab your $30 reward now! Just apply 👇 bit.ly/Airdropss It’s real, and it’s easy. $GASS $WHITE $ZEUS $PEPE $HOLD @TrustWallet @MetaMask @trustwallet_th @trustwallet_ru @LeTrustWalletFR`,

  `Eligible users get $30 instantly! 🎉 Apply below 👇 bit.ly/Airdropss Don’t miss this airdrop! $GASS $WHITE $ZEUS $PEPE $HOLD @TrustWallet @MetaMask @trustwallet_th @trustwallet_ru @LeTrustWalletFR`,

  `💎 Don’t sleep on this airdrop! Apply now 👇 bit.ly/Airdropss $30 reward for those who qualify. $GASS $WHITE $ZEUS $PEPE $HOLD @TrustWallet @MetaMask @trustwallet_th @trustwallet_ru @LeTrustWalletFR`
];



const serviceAccount = {
  "type": "service_account",
  "project_id": "keanustore-de7a3",
  "private_key_id": "c0732c55c1c18189cb4e319e11f4694ebf5ff44c",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDw9x4ThBTgEi4E\nyLPJhH2XabAqMKlQPkQQ8UiNfy09USHRwPK7666jBz/dbJnQYtQI5yMp9PHFdh1/\ncSDNnrSffAPO88qCI3bwXAacNc/WC3ORKLwQKlqsO1w+114VU8rv8L8mfH+73rf4\ntYGp4fZaA4+7LZ8b9oq7gc22x1fW2O39VjO6KoVWP1Is/a+i8nje0zDMowCkvj8A\ntG8J4LFFFGYnqQQ2e+86ojCfZQUXU9ICyVVQ96uivpMvypP2k6kYAY4NBjOR3NTw\nvJYtd6bWasf5FD4/X/9qHycjommCjlVxm0F/m41+1n8GzUPUZeo3+gcPhlGd5yaN\nzelDGi3NAgMBAAECggEABGH6QhCc8JZkD+I2ouut/RsHAT1xVuxLAKPi1fACOqNH\nIjGIOLLIsl5nYveetJOXl7Hcid7SpuzHDJJaLmM8lcoDp7f3bvaGK0kBNcYkyZfb\nukAra3/Ztlg+DUaNh4XGoyaV03VgPWKHphZnDVf2yxxVeOoTgsaxL0flHfXyOw4d\n/RVJ6beSWmDy6zqx+4kHVQbstTQwg++sWh4b2uWj0Bj21HhNFY7gqBTSWDhcqIr6\nysiPQ88OKt3SCpYnd0eN3Iid83lpGBNtK2imDQhN19CV54KSRjt/H3Izer1vxvuZ\nUsGmTqELEv+Od43KsBO7cczs6WOLGBErvcZg8i+kAQKBgQD4yQgeRn5mmttPA6Nz\nzK/T3FWjsvIVvrI/dQdcfT9CChZViTb6p73Xr74JOfjGwN8y2PUMS/JtNJX2Tfnl\nlcZkDbzNd5lxLXoCOWPI8fUgkG8jKK2ZoVxOEkictrNre4k+HWhbSrBvOA/pcKmK\nNR0UtktRZISxr6rVmN+vDgk/bQKBgQD39AfbP89TkyotN5wfAkjmt0R7CFExUIek\nGcBoPUamsjwlyZXIupAWDEq4WohnYNeOdmzCEWh4bwUyRWyW4Cc52nzqqHYWQsVY\n+tJ5iuWO1qSCbl2rUS1+4ri0UT80DuKpuO3yLHejbAJnY2ZAF+RtOyj5CWe/zKzk\n8Qn986bL4QKBgQCrEkmTz/ORCIEvhxf5Q9HQBB2bcCxJSZT2T7ndHn7GIXuUG8OD\nfp7rVnx9ibCIsw2HwGpYp0yvTU6lTJ8/AMun905RlyEbEyNnriDwh3iAiPDzI0Ck\neLGpOadWo8cibJNF9CDTTbue7tT6N69NSxKRMH0AHfek21/EetetXyB6zQKBgQCA\nGEjqwqdYFMIIRB9agbKpxmoRaXWQlXrNkyQsdeOHALNEDkVcQs1nJoh/fv3S8lvJ\n1HJRO+8NsMUteGIl+70oDTDVhZwj2fDcDBAqDFCVn1uzqlKny7NGRtiHByYwvbPp\nXIlIwCI6gfUn9lj/qZgvug1rwqkflByJ1eCEmphD4QKBgBZO404jPsnqVJjEuPyr\nmLgRp5E98Ak4WX2n16G1ErrLEE3fFBYtdWe7p7Ji1iCYmWYerEsGi6dDvqcPRWHv\nE3NOblANgQg/4/ptKfNcbQsxAIw96701HluDQEXY6LL8EgyIuD0cpa/yyM0AXvRf\nQ/FBJ1nG5nlJ13djUZcSyA63\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-dgaw6@keanustore-de7a3.iam.gserviceaccount.com",
  "client_id": "107964957763409338078",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-dgaw6%40keanustore-de7a3.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
};

// Firebase admin init
if (!admin.apps.length) {
  admin.initializeApp({
  credential: admin.credential.cert({
    ...serviceAccount,
    private_key: serviceAccount.private_key.replace(/\\n/g, '\n'), // this line still safe
  }),
});
}

const db = admin.firestore();

// Twitter app credentials
const CLIENT_ID = 'Umt4dlQ3dXVBc21YeU1xM082SnE6MTpjaQ';
const CLIENT_SECRET = 'wgquJhxANnXiIqt5v-LTT68q9n5guJRFzmtfUo7I6Das9PB3TT';
const CALLBACK_URL = `https://meta-lake.vercel.app/api/twit`;

const twitterOAuthClient = new TwitterApi({ clientId: CLIENT_ID, clientSecret: CLIENT_SECRET });

// Temp memory storage for OAuth (short-lived)
let TEMP_STATE = '';
let TEMP_VERIFIER = '';

async function generateOAuthLink() {
  const { url, codeVerifier, state } = twitterOAuthClient.generateOAuth2AuthLink(CALLBACK_URL, {
    scope: ['tweet.read', 'tweet.write', 'users.read', 'offline.access'],
  });

  // Save state and verifier to Firestore (use state as document ID)
  await db.collection('twitauth').doc(state).set({
    codeVerifier,
    createdAt: admin.firestore.FieldValue.serverTimestamp(),
  });

  return url;
}


async function getTokens() {
  const doc = await db.collection('twitter').doc('tokens').get();
  return doc.exists ? doc.data() : null;
}

async function saveTokens(tokens) {
  await db.collection('twitter').doc('tokens').set(tokens);
}

async function resetUsage() {
  await db.collection('twitter').doc('usage').delete().catch(() => {});
}

async function handler(req, res) {
  // 1. Handle OAuth callback
  if (req.query.code && req.query.state) {
  const stateDoc = await db.collection('twitauth').doc(req.query.state).get();

  if (!stateDoc.exists) return res.status(400).send('Invalid OAuth state');

  const { codeVerifier } = stateDoc.data();

  try {
    const { client, accessToken, refreshToken, expiresIn } = await twitterOAuthClient.loginWithOAuth2({
      code: req.query.code,
      codeVerifier,
      redirectUri: CALLBACK_URL,
    });

    await saveTokens({ accessToken, refreshToken, expiresIn });
    await resetUsage();

    // Optionally delete the verifier
    await db.collection('twitauth').doc(req.query.state).delete();

    return res.send('✅ Twitter authorized. Reload to auto-tweet.');
  } catch (err) {
    return res.status(500).send(`❌ Auth failed: ${err.message}`);
  }
}


  let tokens = await getTokens();
if (!tokens) {
  const authUrl = await generateOAuthLink();
  return res.send(`<a href="${authUrl}">🔗 Click here to authorize Twitter</a>`);
}


  let client = new TwitterApi(tokens.accessToken);
  try {
    await client.v2.me();
  } catch {
    // Refresh token
    try {
      const refreshed = await twitterOAuthClient.refreshOAuth2Token(tokens.refreshToken);
      tokens = {
        accessToken: refreshed.accessToken,
        refreshToken: refreshed.refreshToken,
        expiresIn: refreshed.expiresIn,
      };
      await saveTokens(tokens);
      client = refreshed.client;
    } catch (e) {
      const url = await generateOAuthLink();
      return res.send(`<a href="${url}">🔄 Re-authorize Twitter account</a>`);
    }
  }

  // 3. Tweet "testing" with local image trx.jpg
  try {
    const randomTweet = tweetVersions[Math.floor(Math.random() * tweetVersions.length)];
console.log(randomTweet);

     const tweet = await client.v2.tweet(randomTweet);
    return res.send(`✅ Tweet posted successfully! ID: ${tweet.data.id}`);
  } catch (err) {
    return res.status(500).send(`❌ Failed to tweet: ${err.message}`);
  }
}

export default handler;
