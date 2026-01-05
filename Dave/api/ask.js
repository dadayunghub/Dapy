export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).end();

  const { question } = req.body;

  const headers = {
    "Authorization": `Bearer ${process.env.GITHUB_TOKEN}`,
    "Accept": "application/vnd.github+json",
    "Content-Type": "application/json"
  };

  // 1. Dispatch workflow
  await fetch(
    "https://api.github.com/repos/dadayunghub/Ragtest/actions/workflows/download.yml/dispatches",
    {
      method: "POST",
      headers,
      body: JSON.stringify({
        ref: "main",
        inputs: { question }
      })
    }
  );

  // 2. Wait briefly so GitHub registers the run
  await new Promise(r => setTimeout(r, 2000));

  // 3. Get latest run
  const runsRes = await fetch(
    "https://api.github.com/repos/dadayunghub/Ragtest/actions/runs?per_page=1",
    { headers }
  );
  const runs = await runsRes.json();

  const runId = runs.workflow_runs[0].id;

  res.json({ run_id: runId });
}
