/* ============================================================================
   photos.js — Photos des recettes via Supabase Storage
   ----------------------------------------------------------------------------
   À placer dans static/ (build.py le copie dans docs/), à côté de avis.js.

   ⚠️  Renseigne les deux constantes ci-dessous avec la MÊME URL de projet et la
       MÊME clé "sb_publishable_..." que dans avis.js. (Ces valeurs sont
       publiques, c'est normal qu'elles soient dans le code du site.)
   ============================================================================ */

const SUPABASE_URL_PHOTOS = "https://TON-PROJET.supabase.co";   // ← à remplacer
const SUPABASE_KEY_PHOTOS = "TA_CLE_ANON_PUBLIC";               // ← à remplacer

// --- Réglages internes ------------------------------------------------------
const _BUCKET   = "photos";
const _MAX_DIM  = 1280;   // côté le plus long, en pixels, après compression
const _QUALITE  = 0.8;    // qualité JPEG (0–1)
const _PH_REST    = SUPABASE_URL_PHOTOS + "/rest/v1/photos";
const _PH_STORAGE = SUPABASE_URL_PHOTOS + "/storage/v1/object/" + _BUCKET;
const _PH_PUBLIC  = SUPABASE_URL_PHOTOS + "/storage/v1/object/public/" + _BUCKET;
const _PH_HEADERS = {
  "apikey": SUPABASE_KEY_PHOTOS,
  "Authorization": "Bearer " + SUPABASE_KEY_PHOTOS,
};

// Réutilise l'identifiant et le nom déjà posés par avis.js, le cas échéant.
function _phDeviceId() {
  let id = localStorage.getItem("avis_device");
  if (!id) {
    id = "d_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem("avis_device", id);
  }
  return id;
}

function _phConfigOk() {
  return !SUPABASE_URL_PHOTOS.includes("TON-PROJET") && !SUPABASE_KEY_PHOTOS.includes("TA_CLE");
}

// ============================================================================
//  PAGE D'UNE RECETTE  —  appeler initPhotosRecette("slug-de-la-recette")
// ============================================================================

async function initPhotosRecette(slug) {
  const zone = document.getElementById("photos-zone");
  if (!zone) return;
  if (!_phConfigOk()) {
    zone.innerHTML = '<p class="ph-info">Photos non configurées (voir photos.js).</p>';
    return;
  }
  _injecterStylePhotos();

  zone.innerHTML = `
    <h2 class="ph-titre">Photos</h2>
    <div class="ph-galerie" id="ph-galerie"><span class="ph-info">Chargement…</span></div>
    <label class="ph-btn" id="ph-label">
      <span id="ph-btn-txt">+ Ajouter une photo</span>
      <input type="file" id="ph-input" accept="image/*" hidden>
    </label>
    <div id="ph-msg" class="ph-msg"></div>
  `;

  await _afficherGalerie(slug);

  const input = zone.querySelector("#ph-input");
  input.addEventListener("change", () => _envoyerPhoto(slug, input.files[0]));
}

async function _afficherGalerie(slug) {
  const gal = document.getElementById("ph-galerie");
  let photos = [];
  try {
    const r = await fetch(
      `${_PH_REST}?select=*&recette_slug=eq.${encodeURIComponent(slug)}&order=created_at.desc`,
      { headers: _PH_HEADERS }
    );
    photos = await r.json();
  } catch (e) {
    gal.innerHTML = '<span class="ph-info">Photos indisponibles (hors-ligne ?).</span>';
    return;
  }
  if (!photos.length) {
    gal.innerHTML = '<span class="ph-info">Aucune photo pour l\'instant.</span>';
    return;
  }
  gal.innerHTML = photos.map(p => {
    const url = `${_PH_PUBLIC}/${p.chemin}`;
    const leg = p.nom ? ` title="Photo de ${_echapPh(p.nom)}"` : "";
    return `<a href="${url}" target="_blank" rel="noopener" class="ph-vignette"${leg}>
              <img src="${url}" loading="lazy" alt="Photo de la recette">
            </a>`;
  }).join("");
}

async function _envoyerPhoto(slug, file) {
  const msg   = document.getElementById("ph-msg");
  const btnTxt = document.getElementById("ph-btn-txt");
  if (!file) return;
  if (!file.type.startsWith("image/")) { msg.textContent = "Ce fichier n'est pas une image."; return; }

  btnTxt.textContent = "Traitement…";
  msg.textContent = "";
  try {
    // 1. Compression dans le navigateur (réduit fortement le poids envoyé)
    const blob = await _compresser(file, _MAX_DIM, _QUALITE);

    // 2. Nom de fichier organisé par recette : slug/horodatage-aléatoire.jpg
    const alea = Math.random().toString(36).slice(2, 8);
    const chemin = `${slug}/${Date.now()}-${alea}.jpg`;

    // 3. Envoi dans le bucket Storage
    btnTxt.textContent = "Envoi…";
    const up = await fetch(`${_PH_STORAGE}/${chemin}`, {
      method: "POST",
      headers: { ..._PH_HEADERS, "Content-Type": "image/jpeg", "x-upsert": "false" },
      body: blob,
    });
    if (!up.ok) throw new Error("upload " + up.status);

    // 4. Enregistrement de la ligne (lien photo ↔ recette)
    await fetch(_PH_REST, {
      method: "POST",
      headers: { ..._PH_HEADERS, "Content-Type": "application/json", "Prefer": "return=minimal" },
      body: JSON.stringify({
        recette_slug: slug,
        chemin: chemin,
        nom: localStorage.getItem("avis_nom") || null,
        device_id: _phDeviceId(),
      }),
    });

    msg.textContent = "Photo ajoutée, merci !";
    await _afficherGalerie(slug);
  } catch (e) {
    msg.textContent = "Échec de l'envoi (réseau ou format ?).";
  } finally {
    btnTxt.textContent = "+ Ajouter une photo";
    const input = document.getElementById("ph-input");
    if (input) input.value = "";   // permet de renvoyer le même fichier
  }
}

// ============================================================================
//  Compression d'image via <canvas> (aucune bibliothèque externe)
// ============================================================================

function _compresser(file, maxDim, qualite) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      URL.revokeObjectURL(url);
      let w = img.naturalWidth, h = img.naturalHeight;
      if (Math.max(w, h) > maxDim) {
        if (w >= h) { h = Math.round(h * maxDim / w); w = maxDim; }
        else        { w = Math.round(w * maxDim / h); h = maxDim; }
      }
      const c = document.createElement("canvas");
      c.width = w; c.height = h;
      c.getContext("2d").drawImage(img, 0, 0, w, h);
      c.toBlob(b => b ? resolve(b) : reject(new Error("compression")), "image/jpeg", qualite);
    };
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error("image illisible")); };
    img.src = url;
  });
}

// ============================================================================
//  Utilitaires
// ============================================================================

function _echapPh(s) {
  return String(s ?? "").replace(/[&<>"]/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function _injecterStylePhotos() {
  if (document.getElementById("ph-style")) return;
  const css = `
    #photos-zone { margin: 24px 1rem 8px; }
    .ph-titre { font-size: 16px; color: #1b3a5c; margin: 0 0 10px; }
    .ph-galerie { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
    .ph-info { font-size: 12px; color: #aaa; }
    .ph-vignette { display: block; width: 104px; height: 104px; border-radius: 10px;
                   overflow: hidden; background: #e3e9f0; }
    .ph-vignette img { width: 100%; height: 100%; object-fit: cover; display: block; }
    .ph-btn { display: inline-block; background: #1b3a5c; color: #fff; border-radius: 8px;
              padding: 9px 15px; font-size: 14px; font-weight: 500; cursor: pointer; }
    .ph-btn:active { opacity: .85; }
    .ph-msg { font-size: 12px; color: #1b3a5c; margin-top: 8px; min-height: 16px; }
  `;
  const st = document.createElement("style");
  st.id = "ph-style";
  st.textContent = css;
  document.head.appendChild(st);
}
