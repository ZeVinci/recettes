/* ============================================================================
   soumission.js — Soumission de nouvelles recettes par les utilisateurs
   ----------------------------------------------------------------------------
   À placer dans static/ (build.py le copie dans docs/), à côté de avis.js.

   ⚠️  Renseigne SUPABASE_URL_SOUM / SUPABASE_KEY_SOUM avec la MÊME URL de projet
       et la MÊME clé "sb_publishable_..." que dans avis.js (valeurs publiques,
       c'est normal qu'elles soient dans le code).

   📧  ALERTE MAIL (optionnel) : pour être prévenu par mail à chaque soumission,
       crée une clé gratuite sur https://web3forms.com (entre simplement ton
       adresse mail, tu reçois une "Access Key"), puis colle-la dans
       WEB3FORMS_KEY ci-dessous. Laisse "" pour désactiver le mail.
   ============================================================================ */

const SUPABASE_URL_SOUM = "https://knocsfkgsobpfuddoghx.supabase.co";
const SUPABASE_KEY_SOUM  = "sb_publishable__25rgJincAQ4e7WkPFeXRg_ck6Uo9kZ";

const WEB3FORMS_KEY = "";   // ← colle ici ta clé Web3Forms pour recevoir un mail (sinon laisse vide)

// --- Réglages internes ------------------------------------------------------
const _SOUM_API = SUPABASE_URL_SOUM + "/rest/v1/soumissions";
const _SOUM_HEADERS = {
  "apikey": SUPABASE_KEY_SOUM,
  "Authorization": "Bearer " + SUPABASE_KEY_SOUM,
  "Content-Type": "application/json",
};

function _soumConfigOk() {
  return !SUPABASE_URL_SOUM.includes("TON-PROJET") && !SUPABASE_KEY_SOUM.includes("TA_CLE");
}

function _soumEchap(s) {
  return String(s ?? "").replace(/[&<>"]/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

// ============================================================================
//  PAGE FORMULAIRE  —  appeler initFormulaireSoumission()
// ============================================================================

async function initFormulaireSoumission() {
  const zone = document.getElementById("soum-zone");
  if (!zone) return;
  _injecterStyleSoum();

  if (!_soumConfigOk()) {
    zone.innerHTML = '<p class="soum-info">Soumissions non configurées (voir soumission.js).</p>';
    return;
  }

  const nomSauve = localStorage.getItem("avis_nom") || "";

  zone.innerHTML = `
    <div class="soum-form">
      <label class="soum-label">Titre de la recette *</label>
      <input type="text" id="soum-titre" class="soum-input" placeholder="Ex. : Tarte aux courgettes et feta">

      <label class="soum-label">Ingrédients *</label>
      <textarea id="soum-ing" class="soum-input soum-textarea" rows="6"
                placeholder="Un ingrédient par ligne, avec les quantités&#10;Ex. :&#10;- 3 courgettes&#10;- 200 g de feta&#10;- 2 œufs"></textarea>

      <label class="soum-label">Déroulé *</label>
      <textarea id="soum-der" class="soum-input soum-textarea" rows="7"
                placeholder="Les étapes de préparation, dans l'ordre."></textarea>

      <label class="soum-label">Commentaire (facultatif)</label>
      <textarea id="soum-com" class="soum-input soum-textarea" rows="3"
                placeholder="Astuce, origine de la recette, occasion…"></textarea>

      <label class="soum-label">Votre nom (facultatif)</label>
      <input type="text" id="soum-nom" class="soum-input" placeholder="Pour qu'on sache qui propose"
             value="${_soumEchap(nomSauve)}">

      <button id="soum-envoyer" class="soum-btn">Envoyer ma recette</button>
      <div id="soum-msg" class="soum-msg"></div>
    </div>
  `;

  zone.querySelector("#soum-envoyer").addEventListener("click", async () => {
    const titre = zone.querySelector("#soum-titre").value.trim();
    const ing   = zone.querySelector("#soum-ing").value.trim();
    const der   = zone.querySelector("#soum-der").value.trim();
    const com   = zone.querySelector("#soum-com").value.trim();
    const nom   = zone.querySelector("#soum-nom").value.trim();
    const msg   = zone.querySelector("#soum-msg");

    if (!titre || !ing || !der) {
      msg.className = "soum-msg err";
      msg.textContent = "Merci de remplir au moins le titre, les ingrédients et le déroulé.";
      return;
    }
    if (nom) localStorage.setItem("avis_nom", nom);

    const btn = zone.querySelector("#soum-envoyer");
    btn.disabled = true;
    msg.className = "soum-msg";
    msg.textContent = "Envoi…";

    const corps = {
      titre,
      ingredients: ing,
      commentaire: com || null,
      deroule: der,
      soumis_par: nom || null,
    };

    try {
      const r = await fetch(_SOUM_API, {
        method: "POST",
        headers: { ..._SOUM_HEADERS, "Prefer": "return=minimal" },
        body: JSON.stringify(corps),
      });
      if (!r.ok) throw new Error("HTTP " + r.status);

      // Alerte mail facultative (Web3Forms) — n'empêche pas l'enregistrement si elle échoue.
      if (WEB3FORMS_KEY) { _envoyerMail(corps).catch(() => {}); }

      zone.innerHTML = `
        <div class="soum-merci">
          <div class="soum-merci-emoji">🍽️</div>
          <h2>Merci ${nom ? _soumEchap(nom) : ""} !</h2>
          <p>Votre recette « ${_soumEchap(titre)} » a bien été envoyée.<br>
             Elle sera relue puis ajoutée au recueil.</p>
          <a class="soum-btn soum-btn-link" href="index.html">← Retour aux recettes</a>
          <button class="soum-lien" id="soum-encore">Proposer une autre recette</button>
        </div>`;
      const encore = zone.querySelector("#soum-encore");
      if (encore) encore.addEventListener("click", () => initFormulaireSoumission());
    } catch (e) {
      btn.disabled = false;
      msg.className = "soum-msg err";
      msg.textContent = "Échec de l'envoi (réseau ?). Réessayez dans un instant.";
    }
  });
}

// Envoi d'un mail d'alerte via Web3Forms (si une clé est renseignée).
async function _envoyerMail(corps) {
  const texte =
    `Titre : ${corps.titre}\n` +
    `Soumis par : ${corps.soumis_par || "—"}\n\n` +
    `Ingrédients :\n${corps.ingredients}\n\n` +
    `Déroulé :\n${corps.deroule}\n\n` +
    `Commentaire :\n${corps.commentaire || "—"}`;
  await fetch("https://api.web3forms.com/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json", "Accept": "application/json" },
    body: JSON.stringify({
      access_key: WEB3FORMS_KEY,
      subject: "🍽️ Nouvelle recette proposée : " + corps.titre,
      from_name: "Mes recettes",
      message: texte,
    }),
  });
}

// ============================================================================
//  PAGE REVUE (privée)  —  appeler initRevueSoumissions()
// ============================================================================

async function initRevueSoumissions() {
  const zone = document.getElementById("revue-zone");
  if (!zone) return;
  _injecterStyleSoum();

  if (!_soumConfigOk()) {
    zone.innerHTML = '<p class="soum-info">Soumissions non configurées (voir soumission.js).</p>';
    return;
  }

  zone.innerHTML = '<p class="soum-info">Chargement…</p>';

  let liste;
  try {
    const r = await fetch(
      `${_SOUM_API}?select=*&statut=eq.nouveau&order=created_at.asc`,
      { headers: _SOUM_HEADERS }
    );
    liste = await r.json();
  } catch (e) {
    zone.innerHTML = '<p class="soum-info">Impossible de charger (réseau ?).</p>';
    return;
  }

  if (!liste.length) {
    zone.innerHTML = '<p class="soum-info">Aucune nouvelle soumission. ✨</p>';
    return;
  }

  zone.innerHTML = liste.map(s => {
    const date = (s.created_at || "").slice(0, 10);
    return `
    <div class="rev-carte" data-id="${s.id}">
      <div class="rev-haut">
        <span class="rev-titre">${_soumEchap(s.titre)}</span>
        <span class="rev-meta">${_soumEchap(s.soumis_par || "Anonyme")} · ${date}</span>
      </div>
      <div class="rev-bloc"><b>Ingrédients</b><pre>${_soumEchap(s.ingredients || "")}</pre></div>
      <div class="rev-bloc"><b>Déroulé</b><pre>${_soumEchap(s.deroule || "")}</pre></div>
      ${s.commentaire ? `<div class="rev-bloc"><b>Commentaire</b><pre>${_soumEchap(s.commentaire)}</pre></div>` : ""}
      <div class="rev-actions">
        <button class="rev-btn rev-copier" data-id="${s.id}">📋 Copier pour Claude</button>
        <button class="rev-btn rev-traite" data-id="${s.id}">✓ Marquer traité</button>
      </div>
      <div class="rev-msg" id="rev-msg-${s.id}"></div>
    </div>`;
  }).join("");

  const parId = Object.fromEntries(liste.map(s => [String(s.id), s]));

  // « Copier pour Claude » : met la recette au format prêt à coller dans le projet.
  zone.querySelectorAll(".rev-copier").forEach(btn => {
    btn.addEventListener("click", async () => {
      const s = parId[btn.dataset.id];
      const bloc =
`Voici une recette proposée via le formulaire, à mettre au format recettes.md (catégorie à confirmer ensemble, et extrais les « Noms ingrédients » depuis ingredients_recettes.txt) :

# ${s.titre}

## Commentaire

${s.commentaire || ""}

## Ingrédients

${s.ingredients || ""}

## Déroulé de la recette

${s.deroule || ""}

(Proposé par : ${s.soumis_par || "anonyme"})`;
      try {
        await navigator.clipboard.writeText(bloc);
        _revMsg(s.id, "Copié ! Colle-le dans une conversation du projet.");
      } catch (e) {
        // Repli si l'API clipboard est indisponible : on sélectionne dans un textarea.
        const ta = document.createElement("textarea");
        ta.value = bloc; document.body.appendChild(ta); ta.select();
        try { document.execCommand("copy"); _revMsg(s.id, "Copié !"); }
        catch (_) { _revMsg(s.id, "Copie auto impossible — sélectionne le texte à la main."); }
        ta.remove();
      }
    });
  });

  // « Marquer traité » : passe statut à 'traite' (la carte disparaît).
  zone.querySelectorAll(".rev-traite").forEach(btn => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.id;
      _revMsg(id, "Mise à jour…");
      try {
        await fetch(`${_SOUM_API}?id=eq.${id}`, {
          method: "PATCH",
          headers: _SOUM_HEADERS,
          body: JSON.stringify({ statut: "traite" }),
        });
        const carte = zone.querySelector(`.rev-carte[data-id="${id}"]`);
        if (carte) carte.style.display = "none";
        if (!zone.querySelector('.rev-carte:not([style*="display: none"])'))
          zone.innerHTML = '<p class="soum-info">Aucune nouvelle soumission. ✨</p>';
      } catch (e) {
        _revMsg(id, "Échec (réseau ?).");
      }
    });
  });
}

function _revMsg(id, txt) {
  const m = document.getElementById("rev-msg-" + id);
  if (m) m.textContent = txt;
}

// ============================================================================
//  Styles
// ============================================================================

function _injecterStyleSoum() {
  if (document.getElementById("soum-style")) return;
  const css = `
    #soum-zone, #revue-zone { padding: 0 1rem 40px; }
    .soum-form { background: #fff; border: 0.5px solid #d4dde8; border-radius: 12px;
                 padding: 16px; }
    .soum-label { display: block; font-size: 13px; color: #1b3a5c; font-weight: 600;
                  margin: 12px 0 5px; }
    .soum-label:first-child { margin-top: 0; }
    .soum-input { width: 100%; box-sizing: border-box; padding: 10px 11px; font-size: 15px;
                  border: 1px solid #ccc; border-radius: 7px; background: #f9fbfd; }
    .soum-textarea { resize: vertical; font-family: inherit; line-height: 1.4; }
    .soum-btn { display: block; width: 100%; box-sizing: border-box; text-align: center;
                margin-top: 18px; background: #c05a35; color: #fff; border: none;
                border-radius: 9px; padding: 13px 16px; font-size: 15px; font-weight: 600;
                cursor: pointer; text-decoration: none; }
    .soum-btn:disabled { opacity: .6; cursor: default; }
    .soum-btn-link { background: #1b3a5c; }
    .soum-msg { font-size: 13px; color: #1b3a5c; margin-top: 10px; min-height: 18px; }
    .soum-msg.err { color: #c0392b; }
    .soum-info { font-size: 13px; color: #aaa; }
    .soum-merci { background: #fff; border: 0.5px solid #d4dde8; border-radius: 12px;
                  padding: 28px 20px; text-align: center; }
    .soum-merci-emoji { font-size: 44px; }
    .soum-merci h2 { color: #1b3a5c; font-size: 19px; margin: 8px 0 10px; }
    .soum-merci p { color: #555; font-size: 14px; line-height: 1.5; margin: 0 0 18px; }
    .soum-lien { display: block; margin: 14px auto 0; background: none; border: none;
                 color: #c05a35; font-size: 13px; cursor: pointer; text-decoration: underline; }

    .rev-carte { background: #fff; border: 0.5px solid #d4dde8; border-radius: 12px;
                 padding: 14px; margin-bottom: 14px; }
    .rev-haut { display: flex; justify-content: space-between; align-items: baseline;
                gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }
    .rev-titre { font-size: 16px; font-weight: 700; color: #1b3a5c; }
    .rev-meta { font-size: 12px; color: #999; }
    .rev-bloc { margin: 8px 0; }
    .rev-bloc b { font-size: 12px; color: #c05a35; text-transform: uppercase;
                  letter-spacing: .3px; }
    .rev-bloc pre { white-space: pre-wrap; word-wrap: break-word; font-family: inherit;
                    font-size: 13.5px; color: #333; margin: 4px 0 0; line-height: 1.45; }
    .rev-actions { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
    .rev-btn { flex: 1; min-width: 140px; padding: 10px; border-radius: 8px; border: none;
               font-size: 13px; font-weight: 600; cursor: pointer; }
    .rev-copier { background: #1b3a5c; color: #fff; }
    .rev-traite { background: #f0f4f8; color: #1b3a5c; border: 1px solid #d4dde8; }
    .rev-msg { font-size: 12px; color: #1D9E75; margin-top: 8px; min-height: 16px; }
  `;
  const st = document.createElement("style");
  st.id = "soum-style";
  st.textContent = css;
  document.head.appendChild(st);
}
