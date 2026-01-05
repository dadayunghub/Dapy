export default async function handler(req, res) {
  const { artifact_id } = req.body;

  await fetch(
    `https://api.github.com/repos/dadayunghub/Ragtest/actions/artifacts/${artifact_id}`,
    {
      method: "DELETE",
      headers: {
        "Authorization": `Bearer ${process.env.GITHUB_TOKEN}`,
        "Accept": "application/vnd.github+json"
      }
    }
  );

  res.json({ status: "deleted" });
}
