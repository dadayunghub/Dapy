import axios from "axios";

export async function tursoQuery(query, params = []) {
  const db_url = "https://capp-yung.aws-us-east-1.turso.io/v2/pipeline";
  const auth_token = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3NjE0Mjc5MjgsImlkIjoiNDExMWY1Y2EtODkxNC00MTE5LTljZWQtZmM4ODI5ZjAwZTI5IiwicmlkIjoiOGE2YWM5ZTUtMmE3NS00YmIwLWIxMWItOTBkMGJhM2M1Y2U2In0.nSL-kw4pL3A-zEGvKTLOXLlAIqeZi3Xazh0vvwId8jP96xzVeBiCu6c70jzlAtC_qJMlcvx889pz1D0ooT9WBg";

  const payload = {
    requests: [
      {
        type: "execute",
        stmt: { sql: query, args: params.map((v) => ({ type: "text", value: String(v) })) },
      },
    ],
  };

  const res = await fetch(db_url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${auth_token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const decoded = await res.json();
  const result = decoded?.results?.[0]?.response?.result;
  if (!result) return { error: "Unknown result", raw: decoded };

  // SELECT
  if (result.cols && result.rows) {
    const cols = result.cols.map((c) => c.name);
    return result.rows.map((row) => {
      const obj = {};
      cols.forEach((col, i) => (obj[col] = row[i]?.value ?? null));
      return obj;
    });
  }

  // Non-select
  if (result.affected_row_count !== undefined || result.last_insert_rowid !== undefined) {
    return {
      success: true,
      rows_affected: result.affected_row_count ?? 0,
      last_insert_id: result.last_insert_rowid ?? null,
    };
  }

  return { error: "Unknown query type", raw: decoded };
}

export default async function handler(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  const { question, emails, action } = req.body;

  if (!question || !Array.isArray(emails) || emails.length === 0) {
    return res.status(400).json({ error: "email or questions/compliant is missing" });
  }

  // Rate-limit per email
  for (const email of emails) {
    const existing = await tursoQuery(
      "SELECT sendno FROM agent WHERE email = ?",
      [email]
    );

    if (Array.isArray(existing) && existing.length > 0) {
      const sendno = Number(existing[0].sendno);

      if (sendno >= 5) {
        return res.json({
          error: `Rate limit exceeded for ${email}`
        });
      }

      // Update counter
      await tursoQuery(
        "UPDATE agent SET sendno = sendno + 1 WHERE email = ?",
        [email]
      );
    } else {
      // First time email
      await tursoQuery(
        "INSERT INTO agent (email, sendno) VALUES (?, ?)",
        [email, 1]
      );
    }
  }

  // GitHub API headers
  const headers = {
    Authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
    Accept: "application/vnd.github+json",
    "Content-Type": "application/json"
  };

  // 1️⃣ Dispatch workflow ONCE
  await fetch(
    "https://api.github.com/repos/dadayunghub/Ragtest/actions/workflows/portfolio.yml/dispatches",
    {
      method: "POST",
      headers,
      body: JSON.stringify({
        ref: "main",
        inputs: {
          question,
          emails: JSON.stringify(emails), // GitHub Actions needs strings
          action
        }
      })
    }
  );

  // 2️⃣ Wait briefly
  await new Promise(r => setTimeout(r, 2000));

  // 3️⃣ Fetch latest run
  const runsRes = await fetch(
    "https://api.github.com/repos/dadayunghub/Ragtest/actions/runs?per_page=1",
    { headers }
  );

  const runs = await runsRes.json();
  const runId = runs.workflow_runs?.[0]?.id;

  if (!runId) {
    return res.status(500).json({ error: "Failed to get workflow run" });
  }

  res.json({ run_id: runId });
}
