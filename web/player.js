let session = null;
let idx = 0;

function qs(id){ return document.getElementById(id); }

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

function loadCurrent() {
  if (!session) return;
  const it = session.items[idx];
  qs("frame").src = it.url;

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
qs("next").onclick = () => { if (!session) return; idx = Math.min(idx+1, session.items.length-1); loadCurrent(); renderList(); };
qs("prev").onclick = () => { if (!session) return; idx = Math.max(idx-1, 0); loadCurrent(); renderList(); };
qs("open").onclick = () => { if (!session) return; window.open(session.items[idx].url, "_blank", "noreferrer"); };

qs("like").onclick = async () => { await sendFeedback("like"); };
qs("skip").onclick = async () => { await sendFeedback("skip"); qs("next").click(); };
qs("block").onclick = async () => { await sendFeedback("block"); qs("next").click(); };
