/* ============================================================================
   avis.js — Système d'évaluation des recettes via Supabase
   ----------------------------------------------------------------------------
   À placer dans le dossier static/ du projet. build.py le copie dans docs/.

   ⚠️  UNE SEULE CHOSE À FAIRE : renseigne les deux constantes ci-dessous avec
       l'URL de ton projet Supabase et ta clé "anon public" (voir étape 2 du
       guide). Ces deux valeurs sont publiques : il est NORMAL qu'elles soient
       visibles dans le code du site.

   Notation : demi-étoiles autorisées (0,5 à 5). Sur la rangée de saisie,
   un clic sur la moitié GAUCHE d'une étoile donne x,5 ; sur la moitié DROITE,
   x,0. (⚠️ la colonne « note » de la table Supabase doit être de type numeric,
   pas integer — voir le commentaire en bas de fichier.)
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
    if (monAvis) noteChoisie = Number(monAvis.note);
  } catch (e) {
    zone.innerHTML = '<p class="avis-info">Avis indisponibles (hors-ligne ?).</p>';
    return;
  }

  // 2. Construit l'interface
  const nbAvis = mesAvis.length;
  const moyenne = nbAvis ? (mesAvis.reduce((s, a) => s + Number(a.note), 0) / nbAvis) : 0;
  const nomSauve = monAvis?.nom || localStorage.getItem("avis_nom") || "";

  zone.innerHTML = `
    <h2 class="avis-titre">Avis</h2>
    <div class="avis-resume">
      ${nbAvis
        ? `<span class="avis-moy">${_etoilesHTML(moyenne, 16)} ${moyenne.toFixed(1)}</span>
           <span class="avis-nb">· ${nbAvis} avis</span>`
        : `<span class="avis-nb">Aucun avis pour l'instant.</span>`}
    </div>

    <div class="avis-form">
      <div class="avis-form-label">${monAvis ? "Modifier votre note" : "Votre note"}</div>
      <div class="avis-stars" id="avis-stars">
        ${[1,2,3,4,5].map(n =>
          `<span class="avis-star" data-n="${n}"><span class="avis-star-fill"></span></span>`
        ).join("")}
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

  // 3. Étoiles : surbrillance + sélection (avec demi-étoiles)
  const widget = zone.querySelector("#avis-stars");
  const stars = widget.querySelectorAll(".avis-star");

  // Remplit chaque étoile à 0 %, 50 % ou 100 % selon la valeur visée.
  const peindre = (val) => stars.forEach(s => {
    const sn = Number(s.dataset.n);
    const pct = val >= sn ? 100 : (val >= sn - 0.5 ? 50 : 0);
    s.querySelector(".avis-star-fill").style.width = pct + "%";
  });

  // Valeur correspondant à la position du curseur/doigt dans une étoile :
  // moitié gauche → x,5 ; moitié droite → x,0.
  const valeurAu = (s, ev) => {
    const n = Number(s.dataset.n);
    const rect = s.getBoundingClientRect();
    return (ev.clientX - rect.left) < rect.width / 2 ? n - 0.5 : n;
  };

  peindre(noteChoisie);
  stars.forEach(s => {
    // Aperçu au survol (sans effet sur écran tactile, où seul le clic compte).
    s.addEventListener("mousemove", ev => peindre(valeurAu(s, ev)));
    s.addEventListener("click", ev => { noteChoisie = valeurAu(s, ev); peindre(noteChoisie); });
  });
  widget.addEventListener("mouseleave", () => peindre(noteChoisie));

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
        <span class="avis-item-etoiles">${_etoilesHTML(a.note, 12)}</span>
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
    a.somme += Number(l.note); a.n += 1;
  }
  badges.forEach(b => {
    const a = agg[b.dataset.badge];
    if (a && a.n) b.textContent = `★ ${(a.somme / a.n).toFixed(1)} · ${a.n}`;
  });
}

// ============================================================================
//  Utilitaires
// ============================================================================

// Rend 5 étoiles avec remplissage partiel (0 / 50 / 100 %) pour afficher une
// note décimale. `note` peut valoir 4,5 ; on arrondit au demi le plus proche
// pour le visuel (la valeur chiffrée reste affichée à part, ex. « 4,3 »).
function _etoilesHTML(note, taillePx) {
  const px = taillePx || 14;
  const r = Math.round(Number(note) * 2) / 2; // arrondi au 0,5 le plus proche
  let html = `<span class="avis-stars-ro" style="font-size:${px}px">`;
  for (let n = 1; n <= 5; n++) {
    const pct = r >= n ? 100 : (r >= n - 0.5 ? 50 : 0);
    html += `<span class="avis-star"><span class="avis-star-fill" style="width:${pct}%"></span></span>`;
  }
  return html + "</span>";
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

    /* --- Étoiles (saisie + affichage), avec remplissage partiel --- */
    .avis-stars, .avis-stars-ro { display: inline-block; line-height: 1;
                 user-select: none; white-space: nowrap; vertical-align: middle; }
    .avis-stars { font-size: 30px; margin-bottom: 10px; }
    .avis-star { position: relative; display: inline-block; color: #d4dde8; margin: 0 1px; }
    .avis-star::before { content: "\\2605"; }            /* ★ vide (gris) */
    .avis-star-fill { position: absolute; left: 0; top: 0; width: 0;
                 overflow: hidden; color: #f0a500; }
    .avis-star-fill::before { content: "\\2605"; }       /* ★ pleine (orange) */
    #avis-stars .avis-star { cursor: pointer; }          /* cliquable seulement à la saisie */

    .avis-input { width: 100%; box-sizing: border-box; padding: 9px 10px; font-size: 14px;
                  border: 1px solid #ccc; border-radius: 6px; margin-bottom: 8px; }
    .avis-textarea { resize: vertical; font-family: inherit; }
    .avis-btn { background: #1b3a5c; color: #fff; border: none; border-radius: 8px;
                padding: 10px 16px; font-size: 14px; font-weight: 500; cursor: pointer; }
    .avis-msg { font-size: 12px; color: #1b3a5c; margin-top: 8px; min-height: 16px; }
    .avis-item { border-bottom: 0.5px solid #e3e9f0; padding: 10px 0; }
    .avis-item-haut { display: flex; justify-content: space-between; align-items: baseline; }
    .avis-item-nom { font-size: 13px; font-weight: 600; color: #1b3a5c; }
    .avis-item-etoiles { line-height: 1; }
    .avis-item-com { font-size: 13px; color: #333; margin-top: 3px; }
    .avis-info { font-size: 12px; color: #aaa; margin: 0 1rem; }
  `;
  const st = document.createElement("style");
  st.id = "avis-style";
  st.textContent = css;
  document.head.appendChild(st);
}

/* ============================================================================
   ⚠️  CÔTÉ SUPABASE — à faire une seule fois (sinon le 4,5 est refusé) :

   Dans l'éditeur SQL de Supabase, exécuter :

       ALTER TABLE avis ALTER COLUMN note TYPE numeric(2,1);

   Les notes entières déjà enregistrées (4, 5…) restent valides (4.0, 5.0).
   ============================================================================ */
