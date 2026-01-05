import admin from 'firebase-admin';
import fs from 'fs';
import axios from 'axios';

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

const tweetVersions = [
`If you believe you can be a good sissy or femboy, let's create powerful content together — reach out responsibly via https://meettranscel.vercel.app/download/meettrans`,
`If you feel you fit the role of a sissy or femboy and want to collaborate, message responsibly at https://meettranscel.vercel.app/download/meettrans`,
`If you know you can be a great sissy or femboy, let's work on strong content together — contact responsibly through https://meettranscel.vercel.app/download/meettrans`,
`If you're confident in being a sissy or femboy and want to team up, message responsibly via https://meettranscel.vercel.app/download/meettrans`,
`If you see yourself as a good sissy or femboy and want to join in, reach out responsibly at https://meettranscel.vercel.app/download/meettrans`,



];






const mentions = [

`#handjob`,

];



// Run this only once to initialize Firestore
export default async function handler(req, res) {
  try {
    const tweetDoc = await db.collection('transtweetsData').doc('tweetVersions').get();

    if (tweetDoc.exists) {
      console.log('Firestore already initialized. Skipping setup.');
      return res.status(200).send('Firestore already initialized.');
    }

    await db.collection('transtweetsData').doc('tweetVersions').set({
      versions: tweetVersions,
      lastUsedIndex: 0
    });

    await db.collection('transtweetsData').doc('mentions').set({
      list: mentions,
      lastUsedIndex: 0
    });

    console.log('Firestore initialized.');
    return res.status(200).send('Firestore initialized.');
  } catch (err) {
    console.error('Firestore init error:', err);
    return res.status(500).send('Error initializing Firestore');
  }
}
