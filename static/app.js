const form = document.getElementById("scrape-form");
const statusEl = document.getElementById("status");
const outputEl = document.getElementById("json-output");
const analysisEl = document.getElementById("analysis-text");
const copyBtn = document.getElementById("copy-btn");

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const payload = {
    subreddit: document.getElementById("subreddit").value,
    limit: Number(document.getElementById("limit").value),
    time_filter: document.getElementById("time_filter").value,
  };

  statusEl.textContent = "Loading...";
  outputEl.textContent = "";
  analysisEl.value = "";

  try {
    const response = await fetch("/api/scrape", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Request failed");
    }

    statusEl.textContent = data.used_exa
      ? "Done. Exa was used when external URLs were available."
      : "Done. Exa key not found (or no external links), so result is Reddit-only.";

    outputEl.textContent = JSON.stringify(data, null, 2);
    analysisEl.value = data.analysis_text;
  } catch (error) {
    statusEl.textContent = `Error: ${error.message}`;
  }
});

copyBtn.addEventListener("click", async () => {
  if (!analysisEl.value) {
    return;
  }

  await navigator.clipboard.writeText(analysisEl.value);
  copyBtn.textContent = "Copied!";
  setTimeout(() => {
    copyBtn.textContent = "Copy text";
  }, 1200);
});
