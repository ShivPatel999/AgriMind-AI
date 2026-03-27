/**
 * AgriMind AI – Frontend Application
 * Communicates with the FastAPI backend for all AI and weather calls.
 * API key stays server-side — never exposed in the browser.
 */

"use strict";

// ── State ────────────────────────────────────────────────────────────────────

const state = {
  messages: [],          // [{role, content}]
  weatherContext: "",    // Injected into every chat request
  isSending: false,
  weatherOpen: false,
  lastUserInput: null,
};

// ── DOM refs ─────────────────────────────────────────────────────────────────

const $ = id => document.getElementById(id);

// ── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  checkHealth();
  autoDetectWeather();
  $("user-input").focus();
});

// Auto-refresh weather every 10 minutes
setInterval(() => {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      pos => {
        fetchWeatherByCoords(pos.coords.latitude, pos.coords.longitude, true);
      },
      () => {} // Silent fail on refresh; user can manually fetch if needed
    );
  }
}, 10 * 60 * 1000);

// ── Health check (shows RAG status) ─────────────────────────────────────────

async function checkHealth() {
  try {
    const res  = await fetch("/api/health");
    const data = await res.json();
    const docs = data.rag_documents ?? 0;
    $("rag-label").textContent = `${docs.toLocaleString()} ag. docs`;
    $("rag-badge").querySelector(".dot").classList.remove("loading");
  } catch {
    $("rag-label").textContent = "Knowledge base offline";
    $("rag-badge").querySelector(".dot").classList.add("error");
  }
}

// ── Auto-detect weather from browser geolocation ──────────────────────────────

function autoDetectWeather() {
  if (!navigator.geolocation) {
    return; // Geolocation not available; user can manually fetch
  }

  $("weather-label").textContent = "📍 Detecting location…";

  navigator.geolocation.getCurrentPosition(
    (pos) => {
      fetchWeatherByCoords(pos.coords.latitude, pos.coords.longitude, false);
    },
    (err) => {
      // Geolocation denied or error; allow manual fetch
      $("weather-label").textContent = "📍 Turn on location to enable auto-weather";
    }
  );
}

async function fetchWeatherByCoords(latitude, longitude, isRefresh = false) {
  try {
    const res = await fetch("/api/weather/by-coords", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ latitude, longitude }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Location not found");
    }

    const d = await res.json();
    
    if (!isRefresh) {
      // On first load, render the full weather UI if panel is explicitly opened
      renderWeatherCards(d);
    }
    
    state.weatherContext = d.context_string;
    $("weather-label").textContent = `🌍 ${d.location}`;
  } catch (err) {
    if (!isRefresh) {
      $("weather-label").textContent = "📍 Click to add location";
    }
    // Silent fail on refresh
  }
}

// ── Weather panel ─────────────────────────────────────────────────────────────

function toggleWeather() {
  state.weatherOpen = !state.weatherOpen;
  $("weather-panel").classList.toggle("open", state.weatherOpen);
}

async function fetchWeather() {
  const loc = $("loc-input").value.trim();
  if (!loc) { $("loc-input").focus(); return; }

  const btn  = $("loc-btn");
  btn.textContent = "Loading…";
  btn.disabled    = true;

  $("weather-cards").style.display = "none";
  $("weather-flags").style.display = "none";

  try {
    const res  = await fetch("/api/weather", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ location: loc }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Location not found");
    }

    const d = await res.json();
    renderWeatherCards(d);
    state.weatherContext = d.context_string;
    $("weather-label").textContent = `${d.current.emoji} ${d.location}`;

  } catch (err) {
    alert(`⚠️ ${err.message}`);
    $("weather-label").textContent = "Live Weather";
  } finally {
    btn.textContent = "Fetch Weather";
    btn.disabled    = false;
  }
}

function renderWeatherCards(d) {
  const c  = d.current;
  const fc = d.forecast;

  $("weather-cards").innerHTML = `
    <div class="weather-card">
      <div class="wc-label">Temperature</div>
      <div class="wc-value">${c.temperature}°C</div>
      <div class="wc-sub">Current</div>
    </div>
    <div class="weather-card">
      <div class="wc-label">Humidity</div>
      <div class="wc-value">${c.humidity}%</div>
      <div class="wc-sub">${c.humidity > 75 ? "⚠️ High" : "Normal"}</div>
    </div>
    <div class="weather-card">
      <div class="wc-label">Conditions</div>
      <div class="wc-value">${c.emoji}</div>
      <div class="wc-sub">${c.description}</div>
    </div>
    <div class="weather-card">
      <div class="wc-label">Rain Today</div>
      <div class="wc-value">${c.precipitation}<small>mm</small></div>
      <div class="wc-sub">7-day: ${fc.weekly_rain_mm}mm</div>
    </div>
    <div class="weather-card">
      <div class="wc-label">Wind</div>
      <div class="wc-value">${c.wind_speed}</div>
      <div class="wc-sub">km/h</div>
    </div>
    <div class="weather-card">
      <div class="wc-label">Week Temp</div>
      <div class="wc-value">${fc.min_temp}–${fc.max_temp}</div>
      <div class="wc-sub">°C range</div>
    </div>
  `;
  $("weather-cards").style.display = "grid";

  if (d.farming_flags?.length) {
    $("weather-flags").innerHTML = d.farming_flags
      .map(f => `<div class="flag-pill">⚠️ ${f}</div>`)
      .join("");
    $("weather-flags").style.display = "flex";
  }
}

// ── Starter chips ─────────────────────────────────────────────────────────────

function sendStarter(el) {
  // Strip leading emoji + whitespace
  const text = el.textContent.replace(/^[\p{Emoji}\s]+/u, "").trim();
  $("user-input").value = text;
  autoResize($("user-input"));
  sendMessage();
}

// ── Input helpers ─────────────────────────────────────────────────────────────

function autoResize(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 140) + "px";
}

function handleKey(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

// ── Send message ──────────────────────────────────────────────────────────────

async function sendMessage() {
  if (state.isSending) return;

  const input = $("user-input");
  const text  = input.value.trim();
  if (!text) return;

  state.lastUserInput = text;

  // Clear input immediately
  input.value = "";
  input.style.height = "auto";

  // Remove welcome screen on first message
  const welcome = $("welcome");
  if (welcome) welcome.remove();

  // Add user bubble
  appendMsg("user", text);
  state.messages.push({ role: "user", content: text });
  const userMessageIndex = state.messages.length - 1;

  // Lock UI
  state.isSending       = true;
  $("send-btn").disabled = true;
  showTyping();

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);

    const res = await fetch("/api/chat", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body:    JSON.stringify({
        messages:        state.messages,
        weather_context: state.weatherContext,
      }),
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      const detail = await extractErrorDetail(res);
      throw new Error(detail || `Server error ${res.status}`);
    }

    const data  = await res.json();
    const reply = data.reply || "Sorry, I received an empty response. Please try again.";

    removeTyping();
    appendMsg("bot", reply);
    state.messages.push({ role: "assistant", content: reply });
    state.lastUserInput = null;

  } catch (err) {
    removeTyping();

    if (
      userMessageIndex >= 0 &&
      state.messages[userMessageIndex] &&
      state.messages[userMessageIndex].role === "user" &&
      state.messages[userMessageIndex].content === text
    ) {
      state.messages.splice(userMessageIndex, 1);
    }

    const errorMsg = err && err.name === "AbortError"
      ? "Request timed out. Please try again."
      : (err.message || "AI service error. Please try again.");

    const safeMsg = escapeHtml(errorMsg);
    const errHtml = `⚠️ ${safeMsg} <button class="retry-btn" onclick="retryLast()">Retry</button>`;
    appendMsg("bot", errHtml, true);
  } finally {
    state.isSending        = false;
    $("send-btn").disabled  = false;
    input.focus();
  }
}

function retryLast() {
  if (!state.lastUserInput) return;
  $("user-input").value = state.lastUserInput;
  autoResize($("user-input"));
  sendMessage();
}

async function extractErrorDetail(res) {
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    const json = await res.json().catch(() => ({}));
    return json.detail || json.message || "";
  }
  const text = await res.text().catch(() => "");
  return text.trim();
}

// ── Markdown renderer ─────────────────────────────────────────────────────────
// Converts the structured markdown into rich HTML.

function renderMarkdown(text) {
  const lines   = text.split("\n");
  const output  = [];
  let inUl      = false;
  let inOl      = false;
  let olCounter = 1;

  const closeList = () => {
    if (inUl) { output.push("</ul>"); inUl = false; }
    if (inOl) { output.push("</ol>"); inOl = false; olCounter = 1; }
  };

  const inline = str => str
    // Bold
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    // Italic
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    // Inline code
    .replace(/`([^`]+)`/g, "<code>$1</code>");

  for (let i = 0; i < lines.length; i++) {
    const raw  = lines[i];
    const line = raw.trimEnd();

    // Horizontal rule
    if (/^---+$/.test(line.trim())) {
      closeList();
      output.push("<hr>");
      continue;
    }

    // ### Heading → section header
    const h3 = line.match(/^###\s+(.*)/);
    if (h3) {
      closeList();
      output.push(`<div class="md-h3">${inline(h3[1])}</div>`);
      continue;
    }

    // ## Heading
    const h2 = line.match(/^##\s+(.*)/);
    if (h2) {
      closeList();
      output.push(`<div class="md-h3">${inline(h2[1])}</div>`);
      continue;
    }

    // AgriMind Tip line → styled box
    const tip = line.match(/^[\*_]*AgriMind Tip[\*_]*[:\s]+(.*)/i);
    if (tip) {
      closeList();
      output.push(`<div class="tip-box">🌟 <strong>AgriMind Tip:</strong> ${inline(tip[1])}</div>`);
      continue;
    }

    // ⚠️ Watch Out section content → warning box
    // (The header itself renders as md-h3; content below it gets normal list rendering)

    // Numbered list  "1. item" or "1) item"
    const olItem = line.match(/^\d+[.)]\s+(.*)/);
    if (olItem) {
      if (inUl) { output.push("</ul>"); inUl = false; }
      if (!inOl) { output.push('<ol>'); inOl = true; }
      output.push(`<li>${inline(olItem[1])}</li>`);
      continue;
    }

    // Unordered list "- item" or "* item"
    const ulItem = line.match(/^[-*]\s+(.*)/);
    if (ulItem) {
      if (inOl) { output.push("</ol>"); inOl = false; olCounter = 1; }
      if (!inUl) { output.push("<ul>"); inUl = true; }
      output.push(`<li>${inline(ulItem[1])}</li>`);
      continue;
    }

    // Empty line → paragraph break
    if (line.trim() === "") {
      closeList();
      output.push("<br>");
      continue;
    }

    // Regular paragraph
    closeList();
    output.push(`<p>${inline(line)}</p>`);
  }

  closeList();

  // Clean up orphaned <br> at start/end
  let html = output.join("\n");
  html = html.replace(/^(<br>\s*)+/, "").replace(/(<br>\s*)+$/, "");
  return html;
}

// ── DOM helpers ───────────────────────────────────────────────────────────────

function appendMsg(role, text, isError = false) {
  const area = $("chat-area");
  const div  = document.createElement("div");
  div.className = `msg ${role}`;

  if (role === "bot") {
    const bubbleClass = isError ? "bubble error-bubble" : "bubble";
    if (isError) {
      // Error messages may contain small action elements (Retry). Text should be pre-escaped.
      div.innerHTML = `
        <div class="avatar bot">🌾</div>
        <div class="${bubbleClass}">${text}</div>
      `;
    } else {
      div.innerHTML = `
        <div class="avatar bot">🌾</div>
        <div class="${bubbleClass}">${renderMarkdown(text)}</div>
      `;
    }
  } else {
    div.innerHTML = `
      <div class="avatar user-av">👤</div>
      <div class="bubble">${escapeHtml(text).replace(/\n/g, "<br>")}</div>
    `;
  }

  area.appendChild(div);
  area.scrollTop = area.scrollHeight;
}

function showTyping() {
  const area = $("chat-area");
  const div  = document.createElement("div");
  div.className = "msg bot";
  div.id        = "typing-indicator";
  div.innerHTML = `
    <div class="avatar bot">🌾</div>
    <div class="bubble typing"><span></span><span></span><span></span></div>
  `;
  area.appendChild(div);
  area.scrollTop = area.scrollHeight;
}

function removeTyping() {
  const t = $("typing-indicator");
  if (t) t.remove();
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}