/* ============================================================================
   avis.js — Système d'évaluation des recettes via Supabase
   ----------------------------------------------------------------------------
   À placer dans le dossier static/ du projet. build.py le copie dans docs/.

   ⚠️  UNE SEULE CHOSE À FAIRE : renseigne les deux constantes ci-dessous avec
       l'URL de ton projet Supabase et ta clé "anon public" (voir étape 2 du
       guide). Ces deux valeurs sont publiques : il est NORMAL qu'elles soient
       visibles dans le code du site.
   ============================================================================ */

const SUPABASE_URL = "https://knocsfkgsobpfuddoghx.supabase.co";
const SUPABASE_KEY = "sb_publishable__25rgJincAQ4e7WkPFeXRg_ck6Uo9kZ";

// --- Réglages internes ------------------------------------------------------
const _AVIS_API = SUPABASE_URL + "/rest/v1/avis";
const _AVIS_HEADERS = {
  "apikey": SUPABASE_KEY,
  "Authorization": "Bearer " + SUPABASE_KEY,
  "Content-Type": "application/json",
};

// Identifiant anonyme de l'appareil : permet de retrouver / mettre à jour
// l'avis déjà laissé par cette personne, sans créer de compte.
function _deviceId() {
  let id = localStorage.getItem("avis_device");
  if (!id) {
    id = "d_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem("avis_device", id);
  }
  return id;
}

function _configOk() {
  return !SUPABASE_URL.includes("TON-PROJET") && !SUPABASE_KEY.includes("TA_CLE");
}

// ============================================================================
//  PAGE D'UNE RECETTE  —  appeler initAvisRecette("slug-de-la-recette")
// ============================================================================

async function initAvisRecette(slug) {
  const zone = document.getElementById("avis-zone");
  if (!zone) return;
  if (!_configOk()) {
    zone.innerHTML = '<p class="avis-info">Avis non configurés (voir avis.js).</p>';
    return;
  }

  _injecterStyleAvis();

  let mesAvis = [];   // tous les avis de cette recette
  let monAvis = null; // celui de cet appareil, le cas échéant
  let noteChoisie = 0;

  // 1. Récupère les avis existants
  try {
    const r = await fetch(
      `${_AVIS_API}?select=*&recette_slug=eq.${encodeURIComponent(slug)}&order=created_at.desc`,
      { headers: _AVIS_HEADERS }
    );
    mesAvis = await r.json();
    const dev = _deviceId();
    monAvis = mesAvis.find(a => a.device_id === dev) || null;
    if (monAvis) noteChoisie = monAvis.note;
  } catch (e) {
    zone.innerHTML = '<p class="avis-info">Avis indisponibles (hors-ligne ?).</p>';
    return;
  }

  // 2. Construit l'interface
  const nbAvis = mesAvis.length;
  const moyenne = nbAvis ? (mesAvis.reduce((s, a) => s + a.note, 0) / nbAvis) : 0;
  const nomSauve = monAvis?.nom || localStorage.getItem("avis_nom") || "";

  zone.innerHTML = `
    <h2 class="avis-titre">Avis</h2>
    <div class="avis-resume">
      ${nbAvis
        ? `<span class="avis-moy">${_etoilesTexte(moyenne)} ${moyenne.toFixed(1)}</span>
           <span class="avis-nb">· ${nbAvis} avis</span>`
        : `<span class="avis-nb">Aucun avis pour l'instant.</span>`}
    </div>

    <div class="avis-form">
      <div class="avis-form-label">${monAvis ? "Modifier votre note" : "Votre note"}</div>
      <div class="avis-stars" id="avis-stars">
        ${[1,2,3,4,5].map(n => `<span class="avis-star" data-n="${n}">★</span>`).join("")}
      </div>
      <input type="text" id="avis-nom" class="avis-input" placeholder="Votre nom (optionnel)"
             value="${_echap(nomSauve)}">
      <textarea id="avis-com" class="avis-input avis-textarea" rows="3"
                placeholder="Un commentaire ? (optionnel)">${_echap(monAvis?.commentaire || "")}</textarea>
      <button id="avis-envoyer" class="avis-btn">${monAvis ? "Mettre à jour" : "Publier mon avis"}</button>
      <div id="avis-msg" class="avis-msg"></div>
    </div>

    <div class="avis-liste" id="avis-liste">
      ${_listeCommentaires(mesAvis)}
    </div>
  `;

  // 3. Étoiles : surbrillance + sélection
  const stars = zone.querySelectorAll(".avis-star");
  const peindre = (n) => stars.forEach(s =>
    s.classList.toggle("on", Number(s.dataset.n) <= n));
  peindre(noteChoisie);
  stars.forEach(s => {
    s.addEventListener("mouseenter", () => peindre(Number(s.dataset.n)));
    s.addEventListener("click", () => { noteChoisie = Number(s.dataset.n); peindre(noteChoisie); });
  });
  zone.querySelector("#avis-stars").addEventListener("mouseleave", () => peindre(noteChoisie));

  // 4. Envoi (insertion ou mise à jour)
  zone.querySelector("#avis-envoyer").addEventListener("click", async () => {
    const msg = zone.querySelector("#avis-msg");
    if (!noteChoisie) { msg.textContent = "Choisissez un nombre d'étoiles."; return; }
    const nom = zone.querySelector("#avis-nom").value.trim();
    const com = zone.querySelector("#avis-com").value.trim();
    if (nom) localStorage.setItem("avis_nom", nom);

    const corps = { note: noteChoisie, nom: nom || null, commentaire: com || null };
    msg.textContent = "Envoi…";
    try {
      if (monAvis) {
        await fetch(`${_AVIS_API}?id=eq.${monAvis.id}`,
          { method: "PATCH", headers: _AVIS_HEADERS, body: JSON.stringify(corps) });
      } else {
        await fetch(_AVIS_API, {
          method: "POST",
          headers: { ..._AVIS_HEADERS, "Prefer": "return=representation" },
          body: JSON.stringify({ ...corps, recette_slug: slug, device_id: _deviceId() }),
        });
      }
      msg.textContent = "Merci, votre avis est enregistré !";
      setTimeout(() => initAvisRecette(slug), 700); // recharge la section
    } catch (e) {
      msg.textContent = "Échec de l'envoi (réseau ?).";
    }
  });
}

function _listeCommentaires(avis) {
  const avecCom = avis.filter(a => a.commentaire && a.commentaire.trim());
  if (!avecCom.length) return "";
  return avecCom.map(a => `
    <div class="avis-item">
      <div class="avis-item-haut">
        <span class="avis-item-nom">${_echap(a.nom || "Anonyme")}</span>
        <span class="avis-item-etoiles">${"★".repeat(a.note)}${"☆".repeat(5 - a.note)}</span>
      </div>
      <div class="avis-item-com">${_echap(a.commentaire)}</div>
    </div>`).join("");
}

// ============================================================================
//  PAGE D'ACCUEIL (liste)  —  appeler remplirBadgesAvis()
//  Remplit chaque <span class="score-badge" data-badge="slug"></span>
// ============================================================================

async function remplirBadgesAvis() {
  if (!_configOk()) return;
  const badges = document.querySelectorAll("[data-badge]");
  if (!badges.length) return;
  let lignes;
  try {
    const r = await fetch(`${_AVIS_API}?select=recette_slug,note`, { headers: _AVIS_HEADERS });
    lignes = await r.json();
  } catch (e) { return; } // hors-ligne : on n'affiche simplement rien

  // Agrège côté client : moyenne + nombre par slug
  const agg = {};
  for (const l of lignes) {
    const a = agg[l.recette_slug] || (agg[l.recette_slug] = { somme: 0, n: 0 });
    a.somme += l.note; a.n += 1;
  }
  badges.forEach(b => {
    const a = agg[b.dataset.badge];
    if (a && a.n) b.textContent = `★ ${(a.somme / a.n).toFixed(1)} · ${a.n}`;
  });
}

// ============================================================================
//  Utilitaires
// ============================================================================

function _etoilesTexte(moy) {
  const pleines = Math.round(moy);
  return "★".repeat(pleines) + "☆".repeat(5 - pleines);
}

function _echap(s) {
  return String(s ?? "").replace(/[&<>"]/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function _injecterStyleAvis() {
  if (document.getElementById("avis-style")) return;
  const css = `
    #avis-zone { margin: 24px 1rem 40px; }
    .avis-titre { font-size: 16px; color: #1b3a5c; margin: 0 0 8px; }
    .avis-resume { font-size: 14px; color: #555; margin-bottom: 14px; }
    .avis-moy { color: #c05a35; font-weight: 600; }
    .avis-nb { color: #888; }
    .avis-form { background: #fff; border: 0.5px solid #d4dde8; border-radius: 10px;
                 padding: 14px; margin-bottom: 18px; }
    .avis-form-label { font-size: 12px; color: #888; margin-bottom: 6px; }
    .avis-stars { font-size: 30px; line-height: 1; user-select: none; margin-bottom: 10px; }
    .avis-star { color: #d4dde8; cursor: pointer; transition: color .1s; padding: 0 1px; }
    .avis-star.on { color: #f0a500; }
    .avis-input { width: 100%; box-sizing: border-box; padding: 9px 10px; font-size: 14px;
                  border: 1px solid #ccc; border-radius: 6px; margin-bottom: 8px; }
    .avis-textarea { resize: vertical; font-family: inherit; }
    .avis-btn { background: #1b3a5c; color: #fff; border: none; border-radius: 8px;
                padding: 10px 16px; font-size: 14px; font-weight: 500; cursor: pointer; }
    .avis-msg { font-size: 12px; color: #1b3a5c; margin-top: 8px; min-height: 16px; }
    .avis-item { border-bottom: 0.5px solid #e3e9f0; padding: 10px 0; }
    .avis-item-haut { display: flex; justify-content: space-between; align-items: baseline; }
    .avis-item-nom { font-size: 13px; font-weight: 600; color: #1b3a5c; }
    .avis-item-etoiles { font-size: 12px; color: #f0a500; }
    .avis-item-com { font-size: 13px; color: #333; margin-top: 3px; }
    .avis-info { font-size: 12px; color: #aaa; margin: 0 1rem; }
  `;
  const st = document.createElement("style");
  st.id = "avis-style";
  st.textContent = css;
  document.head.appendChild(st);
}
