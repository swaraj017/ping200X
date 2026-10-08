const express = require("express");

const app = express();
const PORT = 3000;

app.use(express.json());

app.get("/health", (req, res) => {
  res.json({
    status: "ok",
  });
});

app.post("/api/check", async (req, res) => {
  const { url } = req.body;

        if (!url) {
        return res.status(400).json({
            error: "URL is required",
        });
        }

        try {
        new URL(url);
        } catch {
        return res.status(400).json({
            error: "Invalid URL",
        });
        }

  const startTime = Date.now();

  try {
    const response = await fetch(url, {
        redirect: "manual",
        signal: AbortSignal.timeout(10000),
        });
    const responseTime = Date.now() - startTime;

    res.json({
      url,
      status: response.ok ? "UP" : "DOWN",
      statusCode: response.status,
      responseTime,
      redirected: response.redirected,
      checkedAt:new Date().toISOString(),
    });
  } catch (error) {

    const responseTime = Date.now() - startTime;

    res.status(200).json({
      url,
      status: "DOWN",
      statusCode: null,
      responseTime,
      error: error.message,
      checkedAt:new Date().toISOString(),
    });
  }
});

app.listen(PORT, () => {
  console.log(`API running on http://localhost:${PORT}`);
});