let session = null;
let idx = 0;
let ytPlayer = null;
let ytApiPromise = null;

function qs(id){ return document.getElementById(id); }

function isVideoEndedMessage(payload) {
  if (!payload) return false;
  if (typeof payload === "string") {
    return payload.includes("VideoEvent: Ended");
  }
  if (typeof payload === "object" && typeof payload.message === "string") {
    return payload.message.includes("VideoEvent: Ended");
  }
  return false;
}

window.addEventListener("message", (event) => {
  if (isVideoEndedMessage(event.data)) {
    const nextBtn = qs("next");
    if (nextBtn) nextBtn.click();
  }
});

window.addEventListener("keydown", (event) => {
  if (!session) return;
  if (event.ctrlKey && (event.key === "ArrowRight" || event.key === "ArrowLeft")) {
    event.preventDefault();
    if (event.key === "ArrowRight") {
      advanceToNext();
    } else {
      idx = Math.max(idx - 1, 0);
      loadCurrent();
      renderList();
    }
    return;
  }
  if (event.key === "ArrowUp") {
    event.preventDefault();
    sendFeedback("like");
    return;
  }
  if (event.key === "ArrowDown") {
    event.preventDefault();
    sendFeedback("skip");
    advanceToNext();
  }
});

function renderList() {
  const itemsDiv = qs("items");
  itemsDiv.innerHTML = "";
  if (!session) return;

  session.items.forEach((it, i) => {
    const div = document.createElement("div");
    div.className = "item" + (i === idx ? " active" : "");
    const t = it.title || it.url;
    div.innerHTML = `<div><strong>${i+1}.</strong> <a href="${it.url}" target="_blank" rel="noreferrer">${escapeHtml(t)}</a></div>
                     <small class="muted">${escapeHtml(it.video_id)}</small>`;
    div.onclick = () => { idx = i; loadCurrent(); renderList(); };
    itemsDiv.appendChild(div);
  });
}

function escapeHtml(s){
  return (s||"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;");
}

function ensureFrameExists() {
  const container = qs("playerContainer");
  let frame = qs("frame");
  if (!frame) {
    frame = document.createElement("iframe");
    frame.id = "frame";
    frame.className = "player";
    frame.referrerPolicy = "no-referrer";
    frame.allow = "autoplay; encrypted-media";
    container.appendChild(frame);
  }
  return frame;
}

function teardownYouTubePlayer() {
  if (ytPlayer) {
    ytPlayer.destroy();
    ytPlayer = null;
  }
  ensureFrameExists();
}

function buildPlayUrl(rawUrl) {
  try {
    const url = new URL(rawUrl, window.location.origin);
    if (url.pathname === "/proxy" && url.searchParams.has("url")) {
      const target = new URL(url.searchParams.get("url"));
      target.searchParams.set("autoplay", "1");
      target.searchParams.set("playsinline", "1");
      url.searchParams.set("url", target.toString());
      return url.toString();
    }
    url.searchParams.set("autoplay", "1");
    url.searchParams.set("playsinline", "1");
    return url.toString();
  } catch (err) {
    return rawUrl;
  }
}

function extractYouTubeId(rawUrl) {
  try {
    const url = new URL(rawUrl);
    const host = url.hostname.toLowerCase();
    if (host === "youtu.be" || host.endsWith(".youtu.be")) {
      return url.pathname.replace("/", "") || null;
    }
    if (host.endsWith("youtube.com")) {
      if (url.pathname === "/watch") {
        return url.searchParams.get("v");
      }
      const parts = url.pathname.split("/").filter(Boolean);
      if (parts[0] === "embed" || parts[0] === "shorts") {
        return parts[1] || null;
      }
    }
  } catch (err) {
    return null;
  }
  return null;
}

function loadYouTubeApi() {
  if (ytApiPromise) return ytApiPromise;
  ytApiPromise = new Promise((resolve) => {
    if (window.YT && window.YT.Player) {
      resolve(window.YT);
      return;
    }
    const tag = document.createElement("script");
    tag.src = "https://www.youtube.com/iframe_api";
    const prior = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => {
      if (typeof prior === "function") prior();
      resolve(window.YT);
    };
    document.head.appendChild(tag);
  });
  return ytApiPromise;
}

async function ensureYouTubePlayer(videoId) {
  await loadYouTubeApi();
  if (!ytPlayer) {
    ytPlayer = new YT.Player("frame", {
      videoId,
      playerVars: { autoplay: 1, playsinline: 1, rel: 0 },
      events: {
        onStateChange: (event) => {
          if (event.data === YT.PlayerState.ENDED) {
            advanceToNext();
          }
        }
      }
    });
  } else {
    ytPlayer.loadVideoById(videoId);
  }
}

function loadCurrent() {
  if (!session) return;
  const it = session.items[idx];
  const playUrl = buildPlayUrl(it.play_url);
  const youtubeId = extractYouTubeId(playUrl);

  if (youtubeId) {
    ensureYouTubePlayer(youtubeId);
  } else {
    teardownYouTubePlayer();
    const frame = ensureFrameExists();
    frame.src = playUrl;
  }

  const ex = it.explain || {};
  qs("meta").innerHTML = `
    <div><strong>${escapeHtml(it.title || "")}</strong></div>
    <div class="muted">${escapeHtml(it.url)}</div>
    <div class="muted">video_id: ${escapeHtml(it.video_id)}</div>
    <div class="muted">tags: ${(ex.tags || []).map(escapeHtml).join(", ")}</div>
  `;

  qs("sessionInfo").innerHTML = `
    <div><strong>Session:</strong> ${escapeHtml(session.session_id)}</div>
    <div><strong>Seed:</strong> ${escapeHtml(session.seed_url)}</div>
  `;
}

function advanceToNext() {
  if (!session) return;
  if (idx >= session.items.length - 1) return;
  idx += 1;
  loadCurrent();
  renderList();
}

async function buildSession() {
  const seed = qs("seed").value.trim();
  const n = parseInt(qs("n").value || "25", 10);
  if (!seed) { alert("Enter a seed URL"); return; }

  qs("go").disabled = true;
  try {
    const url = `/session?seed_url=${encodeURIComponent(seed)}&n=${encodeURIComponent(n)}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(await res.text());
    session = await res.json();
    idx = 0;
    renderList();
    loadCurrent();
  } catch (e) {
    console.error(e);
    alert("Failed to build session: " + e.message);
  } finally {
    qs("go").disabled = false;
  }
}

async function sendFeedback(action) {
  if (!session) return;
  const it = session.items[idx];
  const payload = { session_id: session.session_id, video_id: it.video_id, action };
  await fetch("/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
}

qs("go").onclick = buildSession;
qs("next").onclick = advanceToNext;
qs("prev").onclick = () => { if (!session) return; idx = Math.max(idx-1, 0); loadCurrent(); renderList(); };
qs("open").onclick = () => { if (!session) return; window.open(session.items[idx].url, "_blank", "noreferrer"); };

qs("like").onclick = async () => { await sendFeedback("like"); };
qs("skip").onclick = async () => { await sendFeedback("skip"); advanceToNext(); };
qs("block").onclick = async () => { await sendFeedback("block"); advanceToNext(); };
