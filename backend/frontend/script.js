document.addEventListener("DOMContentLoaded", () => {
  const urlBox = document.getElementById("urlBox");
  const textBox = document.getElementById("textBox");
  const analyzeBtn = document.getElementById("analyzeBtn");
  const clearBtn  = document.getElementById("clearBtn");
  const resultBox = document.getElementById("resultBox");
  const errorBox  = document.getElementById("error");
  const status    = document.getElementById("status");

  function setStatus(type, msg) {
    status.textContent = msg;
    status.className = "pill pill-" + type;
  }

  function setError(msg) {
    if (!msg) {
      errorBox.hidden = true;
      errorBox.textContent = "";
    } else {
      errorBox.hidden = false;
      errorBox.textContent = msg;
    }
  }

  clearBtn.addEventListener("click", () => {
    urlBox.value = "";
    textBox.value = "";
    resultBox.textContent = "No analysis yet.";
    setError("");
    setStatus("warn", "Idle");
  });

  analyzeBtn.addEventListener("click", async () => {
    const url = urlBox.value.trim();
    const text = textBox.value.trim();

    if (!url && !text) {
      setError("Please paste a URL or article text.");
      return;
    }

    setStatus("warn", "Analyzing...");
    setError("");
    analyzeBtn.disabled = true;

    try {
      const res = await fetch("/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, text })
      });


      if (!res.ok) {
        const message = await res.text();
        setError("Server error: " + message);
        setStatus("error", "Error");
        return;
      }

      const data = await res.json();
      resultBox.textContent = JSON.stringify(data, null, 2);
      setStatus("ok", "Done");

    } catch (err) {
      console.error(err);
      setError("Network error.");
      setStatus("error", "Offline");
    } finally {
      analyzeBtn.disabled = false;
    }
  });
});