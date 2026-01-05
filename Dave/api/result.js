import AdmZip from "adm-zip";

export default async function handler(req, res) {
  const run_id = req.query.run_id;

  const headers = {
    Authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
    Accept: "application/vnd.github+json"
  };

  // 1️⃣ Get artifacts
  const artifactsRes = await fetch(
    `https://api.github.com/repos/dadayunghub/Ragtest/actions/runs/${run_id}/artifacts`,
    { headers }
  );

  const artifacts = await artifactsRes.json();
  if (!artifacts.artifacts.length) {
    return res.json({ status: "processing" });
  }

  // 2️⃣ Download artifact ZIP
  const zipRes = await fetch(
    artifacts.artifacts[0].archive_download_url,
    { headers }
  );

  const buffer = Buffer.from(await zipRes.arrayBuffer());
  const zip = new AdmZip(buffer);

  // 3️⃣ Read result.json
  const resultFile = zip.readAsText("result.json");
  const result = JSON.parse(resultFile);

  // 4️⃣ Return only what frontend needs
  res.json({
    status: "done",
    answer: result.answer
  });
}
