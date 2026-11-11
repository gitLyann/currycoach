"use strict";

const chat = document.getElementById("chat");
const form = document.getElementById("form");
const input = document.getElementById("pesan");
const sendButton = document.getElementById("send-button");
const explainToggle = document.getElementById("explain-mode");
const theme = chat.dataset.theme || "currycoach";

function scrollToLatest() { chat.scrollTop = chat.scrollHeight; }

function addMessage(text, sender, options = {}) {
  const row = document.createElement("article");
  row.className = `message-row ${sender}${options.typing ? " typing" : ""}`;
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  bubble.textContent = text;
  row.appendChild(bubble);
  if (options.meta) {
    const meta = document.createElement("small");
    meta.className = "message-meta";
    meta.textContent = options.meta;
    row.appendChild(meta);
  }
  chat.appendChild(row);
  scrollToLatest();
  return row;
}

function addExplainResult(data) {
  if (!Array.isArray(data.candidates) || !data.candidates.length) return;
  const panel = document.createElement("section");
  panel.className = "explain-result";
  const title = document.createElement("strong");
  title.textContent = `Analisis intent · threshold ${Number(data.threshold).toFixed(2)}`;
  panel.appendChild(title);
  data.candidates.slice(0, 3).forEach((candidate) => {
    const line = document.createElement("div");
    line.className = "candidate-line";
    const name = document.createElement("span");
    name.textContent = candidate.intent;
    const score = document.createElement("span");
    score.textContent = `${(Number(candidate.score) * 100).toFixed(1)}%`;
    line.append(name, score);
    panel.appendChild(line);
  });
  chat.appendChild(panel);
  scrollToLatest();
}

async function loadHistory() {
  try {
    const response = await fetch(`/api/history/${encodeURIComponent(theme)}`);
    if (!response.ok) throw new Error("Riwayat tidak dapat dimuat.");
    const data = await response.json();
    if (data.messages && data.messages.length) {
      const welcome = document.getElementById("welcome-card");
      if (welcome) welcome.remove();
      data.messages.forEach((message) => {
        const meta = message.sender === "bot" && message.intent
          ? `Intent: ${message.intent}${message.score !== null ? ` · skor ${(Number(message.score) * 100).toFixed(1)}%` : ""}`
          : "";
        addMessage(message.text, message.sender, { meta });
      });
    } else {
      const welcome = document.getElementById("welcome-card");
      if (welcome) welcome.remove();
      addMessage(chat.dataset.greeting, "bot");
    }
  } catch (error) {
    const welcome = document.getElementById("welcome-card");
    if (welcome) welcome.remove();
    addMessage(chat.dataset.greeting, "bot");
  }
}

async function sendMessage(message) {
  const cleanMessage = message.trim();
  if (!cleanMessage) return;
  const welcome = document.getElementById("welcome-card");
  if (welcome) welcome.remove();
  addMessage(cleanMessage, "user");
  sendButton.disabled = true;
  const typing = addMessage("CurryCoach sedang menyiapkan jawaban...", "bot", { typing: true });
  try {
    const endpoint = explainToggle.checked ? "/api/explain" : "/api/chat";
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: cleanMessage, theme }),
    });
    const data = await response.json();
    typing.remove();
    if (!response.ok) throw new Error(data.error || "Pesan gagal diproses.");
    const meta = `Intent: ${data.intent} · skor ${(Number(data.score) * 100).toFixed(1)}%`;
    addMessage(data.reply, "bot", { meta });
    if (explainToggle.checked) addExplainResult(data);
  } catch (error) {
    typing.remove();
    addMessage(error.message || "Koneksi ke server gagal. Coba lagi sebentar.", "bot");
  } finally {
    sendButton.disabled = false;
    input.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const message = input.value;
  if (!message.trim()) return;
  input.value = "";
  sendMessage(message);
});

document.querySelectorAll(".suggestion-chip").forEach((button) => {
  button.addEventListener("click", () => sendMessage(button.dataset.pesan || ""));
});

document.getElementById("clear-history").addEventListener("click", async () => {
  if (!window.confirm("Hapus semua riwayat percakapan pada sesi ini?")) return;
  try {
    const response = await fetch(`/api/history/${encodeURIComponent(theme)}`, { method: "DELETE" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Riwayat gagal dihapus.");
    chat.replaceChildren();
    addMessage("Riwayat percakapan sudah dibersihkan. Yuk mulai obrolan baru!", "bot");
  } catch (error) {
    window.alert(error.message);
  }
});

loadHistory();
