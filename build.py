"""
build.py — Génère le site statique dans le dossier docs/.
Usage : python build.py
"""
import json
import hashlib
import shutil
import time
from pathlib import Path
import markdown as md_lib
from jinja2 import Environment, BaseLoader
from parser import charger_recettes

RECETTES_MD = Path("recettes.md")
STATIC_SRC  = Path("static")
DOCS        = Path("docs")

ORIGINES = ["Ottolenghi", "Japonais", "Gagnaire", "Breton", "Réunion"]
TYPES    = ["Végé", "Viande", "Poisson", "Dessert"]

# Mot de passe partagé pour accéder au site. Change-le pour ce que tu veux.
# (Tu peux mettre des accents, des espaces, ce que tu préfères.)
MOT_DE_PASSE = "miam"


# ── Template index.html ────────────────────────────────────────────────────────

TMPL_LISTE = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mes recettes</title>
    <link rel="stylesheet" href="style.css">
    <link rel="manifest" href="manifest.json">
    <meta name="theme-color" content="#1b3a5c">
    <style>
        /* ── Base Méditerranée ── */
        body { background: #f0f4f8; }
        header { background: #1b3a5c; }
        header h1 { color: #e8f0f8 !important; }
        #recherche { background: rgba(255,255,255,.12) !important;
                     border-color: rgba(255,255,255,.22) !important;
                     color: #e8f0f8 !important; }
        #recherche::placeholder { color: rgba(232,240,248,.5) !important; }
        #liste-recettes { padding: 6px; }
        #liste-recettes li { background: #fff; border-radius: 10px;
                             border: 0.5px solid #d4dde8; margin-bottom: 6px; }

        /* ── Filtres catégories ── */
        .filter-label { font-size: 11px; color: rgba(232,240,248,.7); margin-bottom: 4px;
                        letter-spacing: 0.04em; margin-top: 8px; }
        .filter-row { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 4px; }
        .chip { display: inline-flex; align-items: center; gap: 4px; padding: 4px 10px;
                border-radius: 99px; font-size: 12px; border: 0.5px solid rgba(255,255,255,.28);
                background: rgba(255,255,255,.12); color: rgba(232,240,248,.85);
                cursor: pointer; user-select: none; }
        .chip .dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
        .dot-origine { background: #e8f0f8; }
        .dot-type    { background: #fdeee8; }
        .chip.active-origine { background: rgba(232,240,248,.2); border-color: rgba(232,240,248,.7); color: #fff; }
        .chip.active-type    { background: rgba(192,90,53,.3); border-color: #d97c5a; color: #fdeee8; }

        /* ── Filtre ingrédients ── */
        .ing-section { margin-top: 8px; }
        .ing-wrap { position: relative; }
        .ing-wrap input { width: 100%; padding: 8px 10px; font-size: 14px;
                          border-radius: 6px; border: 1px solid rgba(255,255,255,.22);
                          background: rgba(255,255,255,.12); color: #e8f0f8; box-sizing: border-box; }
        .ing-wrap input::placeholder { color: rgba(232,240,248,.5); }
        .suggestions { position: absolute; left: 0; right: 0; top: calc(100% + 2px);
                       background: #fff; border: 1px solid #d4dde8; border-radius: 6px;
                       z-index: 100; overflow: hidden; box-shadow: 0 2px 8px rgba(27,58,92,.12); }
        .suggestion { padding: 9px 12px; font-size: 13px; color: #1b3a5c; cursor: pointer;
                      border-bottom: 0.5px solid #eef2f7; }
        .suggestion:last-child { border-bottom: none; }
        .suggestion:hover, .suggestion.focused { background: #f0f4f8; }
        .suggestion mark { background: none; color: #c05a35; font-weight: 500; }
        .ing-tags { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }
        .ing-tag { display: inline-flex; align-items: center; gap: 5px;
                   padding: 3px 8px 3px 10px; border-radius: 99px; font-size: 12px;
                   background: rgba(192,90,53,.25); color: #fde8dc; border: 0.5px solid #d97c5a; }
        .ing-tag button { background: none; border: none; cursor: pointer; color: #fde8dc;
                          font-size: 15px; line-height: 1; padding: 0; }

        /* ── Onglets ── */
        .tabs { display: flex; border-bottom: 0.5px solid #d4dde8;
                background: #f0f4f8; position: sticky; top: 0; z-index: 10; }
        .tab-btn { flex: 1; padding: 11px 8px; font-size: 13px; cursor: pointer;
                   text-align: center; color: #7a95b0; background: #f0f4f8;
                   border: none; position: relative; }
        .tab-btn.active { color: #1b3a5c; font-weight: 500; }
        .tab-btn.active::after { content: ''; position: absolute; bottom: -0.5px;
                                  left: 0; right: 0; height: 2px; background: #1b3a5c; }
        .tab-count { display: inline-block; font-size: 11px; padding: 1px 6px;
                     border-radius: 99px; margin-left: 4px;
                     background: #d4dde8; color: #7a95b0; }
        .tab-btn.active .tab-count { background: #e8f0f8; color: #0c2e4f; }

        /* ── Tags recettes ── */
        .item-tags { display: flex; gap: 4px; flex-wrap: wrap; margin-top: 4px; }
        .tag { font-size: 11px; padding: 2px 7px; border-radius: 99px; }
        .tag-origine { background: #e8f0f8; color: #0c2e4f; }
        .tag-type    { background: #fdeee8; color: #8b3018; }
        .tag-bib     { background: #fdeee8; color: #8b3018; }
        .score-badge { font-size: 10px; padding: 1px 6px; border-radius: 99px; }

        /* ── Mode sélection ── */
        .sel-btn { padding: 6px 10px; font-size: 12px; border-radius: 6px;
                   border: 0.5px solid rgba(255,255,255,.28);
                   background: rgba(255,255,255,.12); color: rgba(232,240,248,.85);
                   cursor: pointer; white-space: nowrap; }
        .sel-btn.on { background: rgba(192,90,53,.3); border-color: #d97c5a; color: #fdeee8; }
        #liste-recettes li.picked { background: #e8f0f8; }
        #liste-recettes li .check-circle { width: 20px; height: 20px; border-radius: 50%;
            border: 1.5px solid #d4dde8; display: none; align-items: center;
            justify-content: center; flex-shrink: 0; margin-right: 4px; }
        body.sel-mode #liste-recettes li .check-circle { display: flex; }
        body.sel-mode #liste-recettes li { cursor: pointer; }
        #liste-recettes li.picked .check-circle { background: #c05a35; border-color: #c05a35; }
        #liste-recettes li.picked .check-circle::after {
            content: '✓'; color: white; font-size: 11px; }

        /* ── Boutons flottants ── */
        .fabs { display: none; position: sticky; bottom: 0; background: #f0f4f8;
                border-top: 0.5px solid #d4dde8; padding: 10px 14px; gap: 8px; }
        .fabs.visible { display: flex; }
        .fab { flex: 1; display: flex; align-items: center; justify-content: center;
               gap: 6px; padding: 10px; border-radius: 99px; font-size: 12px;
               font-weight: 500; border: none; cursor: pointer; text-decoration: none; }
        .fab-menu { background: #1b3a5c; color: white; }
        .fab-ing  { background: #c05a35; color: white; }
        .fab .bdg { background: rgba(255,255,255,.3); border-radius: 99px; font-size: 11px;
                    min-width: 18px; height: 18px; display: flex; align-items: center;
                    justify-content: center; padding: 0 4px; }

        .compteur { text-align: center; color: #7a95b0; font-size: .9rem; margin-top: 1.5rem; }
    </style>
</head>
<body>
    <header>
        <h1>Mes recettes</h1>
        <div style="display:flex;gap:8px;align-items:center;margin-bottom:6px">
            <input type="text" id="recherche" placeholder="Rechercher…"
                   autocomplete="off" style="flex:1">
            <button class="sel-btn" id="sel-btn" onclick="toggleSel()">
                ☑ Sélection
            </button>
        </div>

        <div class="filter-label">Origine</div>
        <div class="filter-row">
            {% for o in origines %}
            <div class="chip" data-val="{{ o }}" data-dim="origine">
                <span class="dot dot-origine"></span>{{ o }}
            </div>
            {% endfor %}
        </div>
        <div class="filter-label">Type</div>
        <div class="filter-row">
            {% for t in types %}
            <div class="chip" data-val="{{ t }}" data-dim="type">
                <span class="dot dot-type"></span>{{ t }}
            </div>
            {% endfor %}
        </div>
        <div class="ing-section">
            <div class="filter-label">Ingrédients dans mon frigo</div>
            <div class="ing-wrap">
                <input type="text" id="ing-input"
                       placeholder="Ex : aubergine, citron…" autocomplete="off">
                <div class="suggestions" id="suggestions"></div>
            </div>
            <div class="ing-tags" id="ing-tags"></div>
        </div>
    </header>

    <!-- Onglets -->
    <div class="tabs">
        <button class="tab-btn active" id="tab-approuvees" onclick="switchTab('approuvees')">
            Mes recettes <span class="tab-count" id="cnt-approuvees">0</span>
        </button>
        <button class="tab-btn" id="tab-bibliotheque" onclick="switchTab('bibliotheque')">
            Bibliothèque <span class="tab-count" id="cnt-bibliotheque">0</span>
        </button>
    </div>

    <ul id="liste-recettes">
        {% for r in recettes %}
        <li data-id="{{ r.id }}"
            data-approuvee="{{ 'true' if r.approuvee else 'false' }}"
            data-tags="{{ r.tags | join(',') }}"
            data-ingredients="{{ r.ingredients | join('|||') }}">
            <div class="check-circle"></div>
            <a href="recettes/{{ r.id }}.html" class="item-link">
                {{ r.titre }}
                <div class="item-tags">
                    {% for tag in r.tags %}
                    {% if tag != 'Pas testé' %}
                    <span class="tag {% if tag in origines %}tag-origine{% else %}tag-type{% endif %}">
                        {{ tag }}
                    </span>
                    {% endif %}
                    {% endfor %}
                    {% if not r.approuvee %}
                    <span class="tag tag-bib">À tester</span>
                    {% endif %}
                </div>
            </a>
        </li>
        {% endfor %}
    </ul>

    <p class="compteur" id="compteur"></p>

    <div class="fabs" id="fabs">
        <a class="fab fab-menu" href="menu.html">
            ☰ Mon menu <span class="bdg" id="bdg-m">0</span>
        </a>
        <a class="fab fab-ing" href="ingredients.html">
            🛒 Ingrédients <span class="bdg" id="bdg-i">0</span>
        </a>
    </div>

    <script>
    const ORIGINES    = {{ origines | tojson }};
    const TOUS_INGR   = {{ tous_ingredients | tojson }};
    const actifs      = new Set();
    const ingActifs   = new Set();
    let texteRecherche = "";
    let modeSel = false;
    let onglet  = "approuvees";   // "approuvees" | "bibliotheque"

    const items    = Array.from(document.querySelectorAll("#liste-recettes li"));
    const compteur = document.getElementById("compteur");

    /* ── Sélection persistante ───────────────────────────────────────────── */
    function getSelection() {
        try { return new Set(JSON.parse(sessionStorage.getItem("sel") || "[]")); }
        catch { return new Set(); }
    }
    function saveSelection(sel) {
        sessionStorage.setItem("sel", JSON.stringify([...sel]));
    }
    let selection = getSelection();

    function updateFabs() {
        const n = selection.size;
        document.getElementById("fabs").classList.toggle("visible", n > 0);
        document.getElementById("bdg-m").textContent = n;
        document.getElementById("bdg-i").textContent = n;
    }

    /* ── Mode sélection ──────────────────────────────────────────────────── */
    function toggleSel() {
        modeSel = !modeSel;
        document.getElementById("sel-btn").classList.toggle("on", modeSel);
        document.body.classList.toggle("sel-mode", modeSel);
    }

    /* ── Onglets ─────────────────────────────────────────────────────────── */
    function switchTab(t) {
        onglet = t;
        document.getElementById("tab-approuvees").className =
            "tab-btn" + (t === "approuvees" ? " active" : "");
        document.getElementById("tab-bibliotheque").className =
            "tab-btn" + (t === "bibliotheque" ? " active" : "");
        filtrer();
    }

    /* ── Score ingrédients ───────────────────────────────────────────────── */
    function scoreIng(li) {
        if (!ingActifs.size) return 1;
        const ingrs = li.dataset.ingredients
            ? li.dataset.ingredients.split("|||") : [];
        return [...ingActifs].filter(q =>
            ingrs.some(i => i.includes(q.toLowerCase()))
        ).length;
    }

    /* ── Filtrage + tri + compteurs ──────────────────────────────────────── */
    function filtrer() {
        const filtresOrigine = [...actifs].filter(v => ORIGINES.includes(v));
        const filtresType    = [...actifs].filter(v => !ORIGINES.includes(v));
        const liste = document.getElementById("liste-recettes");

        let cntApp = 0, cntBib = 0;
        const visibles = [];

        items.forEach(li => {
            const tags      = li.dataset.tags ? li.dataset.tags.split(",") : [];
            const titre     = li.textContent.toLowerCase();
            const approuvee = li.dataset.approuvee === "true";

            const okTexte   = !texteRecherche || titre.includes(texteRecherche);
            const okOrigine = !filtresOrigine.length ||
                              filtresOrigine.every(f => tags.includes(f));
            const okType    = !filtresType.length ||
                              filtresType.every(f => tags.includes(f));
            const s         = scoreIng(li);
            const okIng     = !ingActifs.size || s > 0;

            const passeFiltres = okTexte && okOrigine && okType && okIng;

            // Compteurs dynamiques (toutes recettes passant les filtres)
            if (passeFiltres) {
                if (approuvee)  cntApp++;
                else            cntBib++;
            }

            // Visibilité selon onglet actif
            const dansOnglet = (onglet === "approuvees") === approuvee;
            li.style.display = (passeFiltres && dansOnglet) ? "" : "none";

            if (passeFiltres && dansOnglet) visibles.push({ li, s });
        });

        // Mise à jour des compteurs d'onglets
        document.getElementById("cnt-approuvees").textContent = cntApp;
        document.getElementById("cnt-bibliotheque").textContent = cntBib;

        // Tri par score ingrédients décroissant + badges
        if (ingActifs.size > 0 && visibles.length > 0) {
            visibles.sort((a, b) => b.s - a.s);
            visibles.forEach(({ li, s }) => {
                const old = li.querySelector(".score-badge");
                if (old) old.remove();
                if (ingActifs.size > 1) {
                    const badge = document.createElement("span");
                    badge.className = "score-badge";
                    badge.textContent = s + "/" + ingActifs.size;
                    badge.style.cssText =
                        "background:" + (s === ingActifs.size ? "#fdeee8" : "#FFF3E0") + ";" +
                        "color:"      + (s === ingActifs.size ? "#8b3018" : "#1b3a5c") + ";";
                    li.querySelector(".item-link").appendChild(badge);
                }
                liste.appendChild(li);
            });
        }

        // Compteur global de l'onglet actif
        const total = onglet === "approuvees" ? cntApp : cntBib;
        compteur.textContent = total + " recette" + (total > 1 ? "s" : "");
    }

    /* ── Clic sur une recette ─────────────────────────────────────────────── */
    items.forEach(li => {
        li.addEventListener("click", e => {
            if (!modeSel) return;
            e.preventDefault();
            const id = li.dataset.id;
            selection.has(id) ? selection.delete(id) : selection.add(id);
            li.classList.toggle("picked", selection.has(id));
            saveSelection(selection);
            updateFabs();
        });
    });

    /* ── Restaurer la sélection au chargement ─────────────────────────────── */
    items.forEach(li => {
        if (selection.has(li.dataset.id)) li.classList.add("picked");
    });
    updateFabs();

    /* ── Chips catégories ─────────────────────────────────────────────────── */
    document.querySelectorAll(".chip").forEach(chip => {
        chip.addEventListener("click", () => {
            const val = chip.dataset.val, dim = chip.dataset.dim;
            actifs.has(val) ? actifs.delete(val) : actifs.add(val);
            chip.classList.toggle("active-origine", actifs.has(val) && dim === "origine");
            chip.classList.toggle("active-type",    actifs.has(val) && dim === "type");
            filtrer();
        });
    });

    /* ── Recherche texte ─────────────────────────────────────────────────── */
    document.getElementById("recherche").addEventListener("input", e => {
        texteRecherche = e.target.value.toLowerCase().trim();
        filtrer();
    });

    /* ── Autocomplétion ingrédients ──────────────────────────────────────── */
    const ingInput  = document.getElementById("ing-input");
    const sugBox    = document.getElementById("suggestions");
    const ingTagsEl = document.getElementById("ing-tags");
    let focusedIdx  = -1;

    function highlight(str, q) {
        const i = str.toLowerCase().indexOf(q.toLowerCase());
        if (i < 0) return str;
        return str.slice(0,i) + "<mark>" + str.slice(i, i+q.length) + "</mark>"
             + str.slice(i+q.length);
    }
    function afficherSuggestions(q) {
        if (!q || q.length < 2) { sugBox.innerHTML = ""; return; }
        const matches = TOUS_INGR.filter(i => i.includes(q.toLowerCase())).slice(0,6);
        focusedIdx = -1;
        sugBox.innerHTML = matches.map((m, idx) =>
            `<div class="suggestion" data-val="${m}" data-idx="${idx}">
                ${highlight(m, q)}</div>`).join("");
        sugBox.querySelectorAll(".suggestion").forEach(el =>
            el.addEventListener("mousedown", e => {
                e.preventDefault(); ajouterTag(el.dataset.val); }));
    }
    function ajouterTag(val) {
        ingInput.value = ""; sugBox.innerHTML = "";
        if (ingActifs.has(val)) return;
        ingActifs.add(val);
        const tag = document.createElement("span");
        tag.className = "ing-tag";
        tag.innerHTML = `${val} <button>×</button>`;
        tag.querySelector("button").addEventListener("click", () => {
            ingActifs.delete(val); tag.remove(); filtrer(); });
        ingTagsEl.appendChild(tag);
        filtrer();
    }
    ingInput.addEventListener("input", e => afficherSuggestions(e.target.value.trim()));
    ingInput.addEventListener("keydown", e => {
        const sugs = sugBox.querySelectorAll(".suggestion");
        if (e.key === "ArrowDown") focusedIdx = Math.min(focusedIdx+1, sugs.length-1);
        else if (e.key === "ArrowUp") focusedIdx = Math.max(focusedIdx-1, 0);
        else if (e.key === "Enter") {
            if (focusedIdx >= 0 && sugs[focusedIdx]) ajouterTag(sugs[focusedIdx].dataset.val);
            else if (ingInput.value.trim().length >= 2) ajouterTag(ingInput.value.trim().toLowerCase());
            return;
        } else if (e.key === "Escape") { sugBox.innerHTML = ""; return; }
        sugs.forEach((el, i) => el.classList.toggle("focused", i === focusedIdx));
    });
    ingInput.addEventListener("blur", () =>
        setTimeout(() => { sugBox.innerHTML = ""; }, 150));

    /* ── Init ─────────────────────────────────────────────────────────────── */
    filtrer();

    if ("serviceWorker" in navigator)
        navigator.serviceWorker.register("service-worker.js");
    </script>
</body>
</html>"""


# ── Templates inchangés ────────────────────────────────────────────────────────

TMPL_MENU = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mon menu</title>
    <link rel="stylesheet" href="style.css">
    <link rel="manifest" href="manifest.json">
    <meta name="theme-color" content="#1b3a5c">
    <style>
        /* ── Base Méditerranée ── */
        body { background: #f0f4f8; }
        header { background: #1b3a5c; }
        header h1 { color: #e8f0f8 !important; }
        .bouton-retour { color: rgba(232,240,248,.85) !important; }
        .bouton-retour:hover { color: #fff !important; }
        .mitem { border-bottom: 0.5px solid #eee; padding: 10px 0; display: flex;
                 align-items: center; gap: 10px; }
        .mitem-title { flex: 1; font-size: 14px; }
        .mitem-base { font-size: 11px; color: #aaa; }
        .stepper { display: flex; align-items: center; gap: 6px; }
        .sbtn { width: 26px; height: 26px; border-radius: 50%; border: 0.5px solid #ccc;
                background: #f5f5f5; cursor: pointer; font-size: 16px; line-height: 1;
                display: flex; align-items: center; justify-content: center; }
        .sval { font-size: 13px; font-weight: 500; min-width: 20px; text-align: center; }
        .slbl { font-size: 11px; color: #888; }
        .rm { background: none; border: none; cursor: pointer; color: #ccc;
              font-size: 20px; line-height: 1; padding: 0 2px; }
        .rm:hover { color: #e24b4a; }
        .valider { display: block; width: 100%; padding: 12px; margin-top: 16px;
                   background: #1b3a5c; color: white; border: none; border-radius: 8px;
                   font-size: 14px; font-weight: 500; cursor: pointer; }
        .valider:disabled { opacity: .35; }
        .empty { text-align: center; padding: 2rem; color: #aaa; }
        .nav-ing { display: block; width: 100%; padding: 12px; margin-top: 8px;
                   background: #c05a35; color: white; border: none; border-radius: 8px;
                   font-size: 14px; font-weight: 500; cursor: pointer;
                   text-decoration: none; text-align: center; }
        .tag-bib { background: #fdeee8; color: #8b3018; font-size: 11px;
                   padding: 1px 6px; border-radius: 99px; margin-left: 4px; }
    </style>
</head>
<body>
    <header class="header-recette">
        <a href="index.html" class="bouton-retour">← Retour</a>
        <h1 style="margin-top:8px">Mon menu</h1>
    </header>
    <div style="padding: 0 1rem;">
        <div id="menu-body"></div>
        <button class="valider" id="val-btn" onclick="valider()">
            Valider → liste de courses
        </button>
        <a class="nav-ing" href="ingredients.html">Voir les ingrédients</a>
    </div>
    <script>
    const TOUTES = {{ recettes_json }};
    const couverts = {};
    TOUTES.forEach(r => { couverts[r.id] = r.personnes; });
    function getSelection() {
        try { return new Set(JSON.parse(sessionStorage.getItem("sel") || "[]")); }
        catch { return new Set(); }
    }
    function saveCouverts() {
        sessionStorage.setItem("couverts", JSON.stringify(couverts));
    }
    try {
        const saved = JSON.parse(sessionStorage.getItem("couverts") || "{}");
        Object.assign(couverts, saved);
    } catch {}
    function render() {
        const sel = getSelection();
        const recSel = TOUTES.filter(r => sel.has(String(r.id)));
        document.getElementById("val-btn").disabled = recSel.length === 0;
        if (recSel.length === 0) {
            document.getElementById("menu-body").innerHTML =
                '<p class="empty">Aucune recette sélectionnée.<br>' +
                '<a href="index.html">← Retour à la liste</a></p>';
            return;
        }
        document.getElementById("menu-body").innerHTML = recSel.map(r => `
            <div class="mitem">
                <div style="flex:1">
                    <div class="mitem-title">${r.titre}
                        ${!r.approuvee ? '<span class="tag-bib">À tester</span>' : ''}
                    </div>
                    <div class="mitem-base">Base : ${r.personnes} pers.</div>
                </div>
                <div class="stepper">
                    <button class="sbtn" onclick="changer(${r.id},-1)">−</button>
                    <span class="sval" id="cov-${r.id}">${couverts[r.id]}</span>
                    <span class="slbl">pers.</span>
                    <button class="sbtn" onclick="changer(${r.id},+1)">+</button>
                </div>
                <button class="rm" onclick="retirer(${r.id})">×</button>
            </div>`).join("");
    }
    function changer(id, delta) {
        couverts[id] = Math.max(1, (couverts[id] || 4) + delta);
        const el = document.getElementById("cov-" + id);
        if (el) el.textContent = couverts[id];
        saveCouverts();
    }
    function retirer(id) {
        const sel = getSelection();
        sel.delete(String(id));
        sessionStorage.setItem("sel", JSON.stringify([...sel]));
        render();
    }
    function valider() {
        sessionStorage.setItem("couverts", JSON.stringify(couverts));
        window.location.href = "courses.html";
    }
    render();
    </script>
</body>
</html>"""


TMPL_INGREDIENTS = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ingrédients du menu</title>
    <link rel="stylesheet" href="style.css">
    <link rel="manifest" href="manifest.json">
    <meta name="theme-color" content="#1b3a5c">
    <style>
        /* ── Base Méditerranée ── */
        body { background: #f0f4f8; }
        header { background: #1b3a5c; }
        header h1 { color: #e8f0f8 !important; }
        .bouton-retour { color: rgba(232,240,248,.85) !important; }
        .bouton-retour:hover { color: #fff !important; }
        .sec { font-size: 10px; color: #aaa; letter-spacing: .05em;
               padding: 10px 0 3px; text-transform: uppercase; }
        .iitem { border-bottom: 0.5px solid #eee; padding: 9px 0;
                 display: flex; align-items: baseline; gap: 8px; }
        .iqte { font-size: 12px; font-weight: 500; color: #555; min-width: 80px; }
        .inom { font-size: 13px; color: #222; }
        .valider { display: block; width: 100%; padding: 12px; margin-top: 16px;
                   background: #1b3a5c; color: white; border: none; border-radius: 8px;
                   font-size: 14px; font-weight: 500; cursor: pointer; }
    </style>
</head>
<body>
    <header class="header-recette">
        <a href="menu.html" class="bouton-retour">← Mon menu</a>
        <h1 style="margin-top:8px">Ingrédients</h1>
        <p id="sub" style="font-size:12px;color:#888;margin-top:4px"></p>
    </header>
    <div style="padding: 0 1rem;">
        <div id="ing-body"></div>
        <button class="valider" onclick="valider()">Valider → liste de courses</button>
    </div>
    <script>
    const TOUTES = {{ recettes_json }};
    function getSelection() {
        try { return new Set(JSON.parse(sessionStorage.getItem("sel") || "[]")); }
        catch { return new Set(); }
    }
    function getCouverts() {
        try { return JSON.parse(sessionStorage.getItem("couverts") || "{}"); }
        catch { return {}; }
    }
    function fmtQte(qte, unite, ratio) {
        if (!qte) return '';
        const q = Math.round(qte * ratio * 10) / 10;
        return q + (unite ? '\\u00a0' + unite : '');
    }
    function render() {
        const sel = getSelection(), couverts = getCouverts();
        const recSel = TOUTES.filter(r => sel.has(String(r.id)));
        document.getElementById("sub").textContent =
            recSel.length + " recette" + (recSel.length > 1 ? "s" : "");
        document.getElementById("ing-body").innerHTML = recSel.map(r => {
            const cv = couverts[r.id] || r.personnes;
            const ratio = cv / r.personnes;
            return `<div class="sec">${r.titre} — ${cv} pers.</div>` +
                r.ingredients_qte.map(i => `
                    <div class="iitem">
                        <span class="iqte">${fmtQte(i.qte, i.unite, ratio)}</span>
                        <span class="inom">${i.nom}</span>
                    </div>`).join('');
        }).join('');
    }
    function valider() { window.location.href = "courses.html"; }
    render();
    </script>
</body>
</html>"""


TMPL_COURSES = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Liste de courses</title>
    <link rel="stylesheet" href="style.css">
    <link rel="manifest" href="manifest.json">
    <meta name="theme-color" content="#1b3a5c">
    <style>
        /* ── Base Méditerranée ── */
        body { background: #f0f4f8; }
        header { background: #1b3a5c; }
        header h1 { color: #e8f0f8 !important; }
        .bouton-retour { color: rgba(232,240,248,.85) !important; }
        .bouton-retour:hover { color: #fff !important; }
        .toolbar { display: flex; gap: 8px; margin-bottom: 10px; flex-wrap: wrap; }
        .tbtn { flex: 1; padding: 8px 10px; border-radius: 6px; border: 0.5px solid #ccc;
                background: #f5f5f5; color: #555; font-size: 12px; cursor: pointer; }
        .tbtn.primary   { background: #1b3a5c; color: white; border-color: #1b3a5c; }
        .tbtn.secondary { background: #c05a35; color: white; border-color: #c05a35; }
        .add-row { display: flex; gap: 8px; margin-bottom: 12px; }
        .add-row input { flex: 1; padding: 8px 10px; font-size: 14px; border-radius: 6px;
                         border: 1px solid #ccc; background: #f9f9f9; }
        .add-row button { padding: 8px 14px; background: #1b3a5c; color: white;
                          border: none; border-radius: 6px; font-size: 18px; cursor: pointer; }
        .citem { border-bottom: 0.5px solid #eee; padding: 10px 0; display: flex;
                 align-items: center; gap: 10px; cursor: grab; user-select: none; }
        .citem.raye .clabel, .citem.raye .cqty { text-decoration: line-through; color: #aaa; }
        .ccheck { width: 22px; height: 22px; border-radius: 50%; border: 1.5px solid #ccc;
                  flex-shrink: 0; display: flex; align-items: center;
                  justify-content: center; cursor: pointer; }
        .citem.raye .ccheck { background: #1D9E75; border-color: #1D9E75; }
        .ccheck-inner { font-size: 12px; color: white; display: none; }
        .citem.raye .ccheck-inner { display: block; }
        .dragh { color: #ccc; font-size: 16px; }
        .clabel { flex: 1; font-size: 14px; }
        .cqty { font-size: 12px; color: #888; }
        .crm { background: none; border: none; cursor: pointer; color: #ccc;
               font-size: 20px; line-height: 1; padding: 0 2px; }
        .crm:hover { color: #e24b4a; }
        .sub { font-size: 12px; color: #888; margin-top: 4px; }
        .empty { text-align: center; padding: 2rem; color: #aaa; }
        .drag-over { border-top: 2px solid #1b3a5c; }
        .panel { display: none; background: #fafafa; border: 0.5px solid #eee;
                 border-radius: 8px; padding: 12px; margin-bottom: 12px; }
        .panel.open { display: block; }
        .panel h3 { font-size: 13px; font-weight: 500; margin-bottom: 10px; color: #333; }
        .modal-bg { display: none; position: fixed; inset: 0; background: rgba(0,0,0,.4);
                    z-index: 200; align-items: center; justify-content: center; }
        .modal-bg.open { display: flex; }
        .modal { background: white; border-radius: 10px; padding: 20px;
                 width: 280px; max-width: 90vw; }
        .modal h3 { font-size: 15px; font-weight: 500; margin-bottom: 12px; }
        .modal input { width: 100%; padding: 8px 10px; font-size: 14px; border-radius: 6px;
                       border: 1px solid #ccc; margin-bottom: 12px; box-sizing: border-box; }
        .modal-btns { display: flex; gap: 8px; }
        .modal-btns button { flex: 1; padding: 10px; border-radius: 6px;
                             font-size: 13px; cursor: pointer; border: none; }
        .btn-cancel { background: #f5f5f5; color: #555; }
        .btn-ok     { background: #1b3a5c; color: white; }
    </style>
</head>
<body>
    <header class="header-recette">
        <a href="menu.html" class="bouton-retour">← Mon menu</a>
        <h1 style="margin-top:8px">Liste de courses</h1>
        <p class="sub" id="sub"></p>
    </header>
    <div style="padding: 0 1rem;">
        <div class="toolbar">
            <button class="tbtn primary"   onclick="demanderNomSauvegarde()">↓ Sauvegarder</button>
            <button class="tbtn secondary" onclick="togglePanel()">↑ Charger une liste</button>
        </div>
        <div class="panel" id="panel-listes">
            <h3>Charger une liste</h3>
            <p style="font-size:13px;color:#555;margin-bottom:10px">
                Sélectionne un fichier .json sauvegardé précédemment :
            </p>
            <input type="file" accept=".json" id="file-inp" style="font-size:13px;width:100%"
                   onchange="chargerFichier(this)">
        </div>
        <div class="add-row">
            <input type="text" id="add-inp" placeholder="Ajouter un ingrédient…">
            <button onclick="ajouter()">+</button>
        </div>
        <div id="courses-body"></div>
    </div>
    <div class="modal-bg" id="modal-bg">
        <div class="modal">
            <h3>Nom de la liste</h3>
            <input type="text" id="modal-inp" placeholder="Ex : Semaine du 20 mai…" maxlength="50">
            <div class="modal-btns">
                <button class="btn-cancel" onclick="fermerModal()">Annuler</button>
                <button class="btn-ok"     onclick="sauvegarderListe()">Sauvegarder</button>
            </div>
        </div>
    </div>
    <script>
    const TOUTES = {{ recettes_json }};
    let courses = [], dragIdx = null;
    function getSelection() {
        try { return new Set(JSON.parse(sessionStorage.getItem("sel") || "[]")); }
        catch { return new Set(); }
    }
    function getCouverts() {
        try { return JSON.parse(sessionStorage.getItem("couverts") || "{}"); }
        catch { return {}; }
    }
    function saveCourses() { sessionStorage.setItem("courses", JSON.stringify(courses)); }
    function loadSessionCourses() {
        try { const s = JSON.parse(sessionStorage.getItem("courses")); if (s && s.length > 0) return s; }
        catch {} return null;
    }
    function genererCourses() {
        const sel = getSelection(), couverts = getCouverts();
        const recSel = TOUTES.filter(r => sel.has(String(r.id)));
        const map = {};
        recSel.forEach(r => {
            const ratio = (couverts[r.id] || r.personnes) / r.personnes;
            r.ingredients_qte.forEach(i => {
                const key = i.nom_cure || i.nom;
                if (!map[key]) map[key] = { nom: key, entrees: [] };
                map[key].entrees.push({ qte: i.qte ? i.qte * ratio : null, unite: i.unite });
            });
        });
        courses = Object.values(map).map(({ nom, entrees }) => {
            const us = [...new Set(entrees.map(e => e.unite).filter(Boolean))];
            let qteStr = '';
            if (us.length === 1) {
                const t = Math.round(entrees.reduce((s,e) => s+(e.qte||0), 0) * 10) / 10;
                qteStr = t > 0 ? t + '\\u00a0' + us[0] : '';
            } else if (us.length === 0) {
                const t = Math.round(entrees.reduce((s,e) => s+(e.qte||0), 0) * 10) / 10;
                qteStr = t > 0 ? String(t) : '';
            } else {
                qteStr = entrees.map(e => e.qte
                    ? (Math.round(e.qte*10)/10) + (e.unite ? '\\u00a0'+e.unite : '') : '')
                    .filter(Boolean).join(' + ');
            }
            return { nom, qteStr, raye: false };
        }).sort((a, b) => a.nom.localeCompare(b.nom, 'fr'));
        saveCourses();
    }
    function render() {
        const restants = courses.filter(i => !i.raye).length;
        document.getElementById("sub").textContent =
            restants + "/" + courses.length +
            " élément" + (courses.length !== 1 ? "s" : "") + " restant";
        const el = document.getElementById("courses-body");
        if (!courses.length) { el.innerHTML = '<div class="empty">Liste vide</div>'; return; }
        el.innerHTML = courses.map((item, idx) => `
            <div class="citem ${item.raye ? 'raye' : ''}" draggable="true" data-idx="${idx}">
                <span class="dragh">⠿</span>
                <div class="ccheck" onclick="rayer(${idx})">
                    <span class="ccheck-inner">✓</span>
                </div>
                <span class="clabel">${item.nom}</span>
                ${item.qteStr ? `<span class="cqty">${item.qteStr}</span>` : ''}
                <button class="crm" onclick="retirer(${idx})">×</button>
            </div>`).join('');
        el.querySelectorAll('.citem').forEach(row => {
            row.addEventListener('dragstart', () => { dragIdx = +row.dataset.idx; row.style.opacity = '.4'; });
            row.addEventListener('dragend',   () => { row.style.opacity = ''; });
            row.addEventListener('dragover',  e => { e.preventDefault(); row.classList.add('drag-over'); });
            row.addEventListener('dragleave', () => { row.classList.remove('drag-over'); });
            row.addEventListener('drop', e => {
                e.preventDefault(); row.classList.remove('drag-over');
                const dest = +row.dataset.idx;
                if (dragIdx === dest) return;
                const moved = courses.splice(dragIdx, 1)[0];
                courses.splice(dest, 0, moved);
                saveCourses(); render();
            });
        });
    }
    function rayer(idx)   { courses[idx].raye = !courses[idx].raye; saveCourses(); render(); }
    function retirer(idx) { courses.splice(idx, 1); saveCourses(); render(); }
    function ajouter() {
        const inp = document.getElementById("add-inp"), val = inp.value.trim();
        if (!val) return;
        courses.push({ nom: val, qteStr: '', raye: false });
        inp.value = ''; saveCourses(); render();
    }
    document.getElementById("add-inp").addEventListener("keydown", e => {
        if (e.key === "Enter") ajouter(); });
    function demanderNomSauvegarde() {
        if (!courses.length) { alert("La liste est vide."); return; }
        const today = new Date().toLocaleDateString('fr-FR', { day: 'numeric', month: 'long' });
        document.getElementById("modal-inp").value = "Courses du " + today;
        document.getElementById("modal-bg").classList.add("open");
        setTimeout(() => document.getElementById("modal-inp").select(), 50);
    }
    function fermerModal() { document.getElementById("modal-bg").classList.remove("open"); }
    function sauvegarderListe() {
        const nom = document.getElementById("modal-inp").value.trim();
        if (!nom) return;
        fermerModal();
        const recSel = TOUTES.filter(r => getSelection().has(String(r.id))).map(r => r.titre);
        const data = { version: 1, nom, date: new Date().toISOString(), recettes: recSel, articles: courses };
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = nom.replace(/[^a-zA-Z0-9 -]/g, '').trim().replace(/ +/g, '_') + ".json";
        a.click(); URL.revokeObjectURL(url);
    }
    function togglePanel() { document.getElementById("panel-listes").classList.toggle("open"); }
    function chargerFichier(input) {
        const file = input.files[0]; if (!file) return;
        const reader = new FileReader();
        reader.onload = e => {
            try {
                const data = JSON.parse(e.target.result);
                if (!data.articles || !Array.isArray(data.articles)) throw new Error();
                courses = data.articles; saveCourses(); render();
                document.getElementById("panel-listes").classList.remove("open");
                const date = data.date ? new Date(data.date).toLocaleDateString('fr-FR',
                    { day: 'numeric', month: 'long', year: 'numeric' }) : '';
                alert('Liste "' + data.nom + '" chargée' + (date ? ' (' + date + ')' : '') + '.');
            } catch { alert("Fichier invalide."); }
        };
        reader.readAsText(file);
    }
    document.getElementById("modal-inp").addEventListener("keydown", e => {
        if (e.key === "Enter") sauvegarderListe();
        if (e.key === "Escape") fermerModal();
    });
    document.getElementById("modal-bg").addEventListener("click", e => {
        if (e.target === e.currentTarget) fermerModal(); });
    const saved = loadSessionCourses();
    if (saved) { courses = saved; render(); }
    else { genererCourses(); render(); }
    </script>
</body>
</html>"""


TMPL_RECETTE = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ titre }}</title>
    <link rel="stylesheet" href="../style.css">
    <link rel="manifest" href="../manifest.json">
    <meta name="theme-color" content="#1b3a5c">
    <style>
        body { background: #f0f4f8; }
        header { background: #1b3a5c; }
        .bouton-retour { color: rgba(232,240,248,.85) !important; }
        .bouton-retour:hover { color: #fff !important; }
    </style>
</head>
<body>
    <header class="header-recette">
        <a href="../index.html" class="bouton-retour">← Retour</a>
    </header>
    <article class="recette">
        {{ contenu_html }}
    </article>
</body>
</html>"""


# ── Portail mot de passe (injecté sur chaque page) ──────────────────────────────
# Le marqueur __HASH__ est remplacé au build par le hash SHA-256 du mot de passe.
# Le mot de passe en clair n'apparaît donc jamais dans les pages publiées.

GATE_HTML = """
<style>
  html.verrouille body > *:not(#porte) { display: none !important; }
  #porte { display: none; }
  html.verrouille #porte {
    display: flex; position: fixed; inset: 0; z-index: 99999;
    align-items: center; justify-content: center; background: #faf8f5;
    font-family: -apple-system, system-ui, sans-serif;
  }
  #porte .boite { width: 100%; max-width: 300px; padding: 24px; text-align: center; }
  #porte h2 { margin: 0 0 16px; font-size: 18px; color: #5a3a1a; font-weight: 600; }
  #porte input { width: 100%; padding: 12px; font-size: 16px; box-sizing: border-box;
    border: 1px solid #d8cfc4; border-radius: 8px; background: #fff; margin-bottom: 10px; }
  #porte button { width: 100%; padding: 12px; font-size: 15px; border: none;
    border-radius: 8px; background: #1b3a5c; color: #fff; cursor: pointer; }
  #porte .err { color: #c0392b; font-size: 13px; height: 16px; margin-bottom: 8px; }
</style>
<script>
(function () {
  var HASH = "__HASH__";
  var CLE = "recettes_acces";
  if (localStorage.getItem(CLE) === HASH) return;        // déjà entré : on laisse passer
  document.documentElement.classList.add("verrouille");  // sinon on masque tout de suite

  async function sha256(txt) {
    var buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(txt));
    return Array.from(new Uint8Array(buf))
      .map(function (b) { return b.toString(16).padStart(2, "0"); }).join("");
  }

  function poser() {
    var d = document.createElement("div");
    d.id = "porte";
    d.innerHTML =
      '<div class="boite">' +
      '<h2>\\uD83D\\uDD12 Mes recettes</h2>' +
      '<div class="err" id="porte-err"></div>' +
      '<input type="password" id="porte-mdp" placeholder="Mot de passe" autocomplete="current-password">' +
      '<button id="porte-ok">Entrer</button></div>';
    document.body.appendChild(d);
    var inp = document.getElementById("porte-mdp");
    var err = document.getElementById("porte-err");
    inp.focus();
    async function verifier() {
      var h = await sha256(inp.value);
      if (h === HASH) {
        localStorage.setItem(CLE, HASH);
        document.documentElement.classList.remove("verrouille");
        d.remove();
      } else {
        err.textContent = "Mot de passe incorrect";
        inp.value = ""; inp.focus();
      }
    }
    document.getElementById("porte-ok").addEventListener("click", verifier);
    inp.addEventListener("keydown", function (e) { if (e.key === "Enter") verifier(); });
  }
  if (document.body) poser();
  else document.addEventListener("DOMContentLoaded", poser);
})();
</script>
"""


# ── Build ──────────────────────────────────────────────────────────────────────

def build():
    # 1. Nettoyage
    if DOCS.exists():
        for _ in range(5):
            try: shutil.rmtree(DOCS); break
            except PermissionError: time.sleep(0.5)
        else:
            for f in DOCS.rglob("*"):
                if f.is_file(): f.unlink(missing_ok=True)
    DOCS.mkdir(exist_ok=True)
    (DOCS / "recettes").mkdir(exist_ok=True)

    # 2. Fichiers statiques
    for f in STATIC_SRC.iterdir():
        shutil.copy(f, DOCS / f.name)

    # 3. Recettes
    recettes = charger_recettes(RECETTES_MD)
    nb_app = sum(1 for r in recettes if r["approuvee"])
    nb_bib = sum(1 for r in recettes if not r["approuvee"])
    print(f"{len(recettes)} recettes — {nb_app} approuvées, {nb_bib} bibliothèque.")

    # 4. Ingrédients uniques pour l'autocomplétion
    import unicodedata
    def norm(s):
        n = unicodedata.normalize("NFD", s.lower())
        return "".join(c for c in n if unicodedata.category(c) != "Mn")

    ing_set = set()
    for r in recettes: ing_set.update(r["ingredients"])
    tous_ingredients = sorted(ing_set, key=norm)
    print(f"{len(tous_ingredients)} ingrédients uniques.")

    # 5. JSON des recettes
    def recette_json(r):
        ing_qte_enrichis = []
        cures_set = set(r["ingredients"])
        for i in r["ingredients_qte"]:
            nom_cure = None
            for mc in cures_set:
                if norm(mc) in norm(i["nom"]):
                    nom_cure = mc; break
            ing_qte_enrichis.append({
                "nom":      i["nom"],
                "nom_cure": nom_cure or i["nom"],
                "qte":      i["qte"],
                "unite":    i["unite"],
            })
        return {
            "id":              r["id"],
            "titre":           r["titre"],
            "tags":            r["tags"],
            "approuvee":       r["approuvee"],
            "personnes":       r["personnes"],
            "ingredients":     r["ingredients"],
            "ingredients_qte": ing_qte_enrichis,
        }

    recettes_data     = [recette_json(r) for r in recettes]
    recettes_json_str = json.dumps(recettes_data, ensure_ascii=False)

    env = Environment(loader=BaseLoader())
    env.filters["tojson"] = json.dumps

    # 6. index.html
    tmpl = env.from_string(TMPL_LISTE)
    (DOCS / "index.html").write_text(
        tmpl.render(recettes=recettes, origines=ORIGINES, types=TYPES,
                    tous_ingredients=tous_ingredients),
        encoding="utf-8")

    # 7. menu.html
    tmpl = env.from_string(TMPL_MENU)
    (DOCS / "menu.html").write_text(
        tmpl.render(recettes_json=recettes_json_str), encoding="utf-8")

    # 8. ingredients.html
    tmpl = env.from_string(TMPL_INGREDIENTS)
    (DOCS / "ingredients.html").write_text(
        tmpl.render(recettes_json=recettes_json_str), encoding="utf-8")

    # 9. courses.html
    tmpl = env.from_string(TMPL_COURSES)
    (DOCS / "courses.html").write_text(
        tmpl.render(recettes_json=recettes_json_str), encoding="utf-8")

    # 10. Pages recettes individuelles
    tmpl = env.from_string(TMPL_RECETTE)
    for r in recettes:
        html = md_lib.markdown(r["contenu_md"], extensions=["extra", "sane_lists"])
        (DOCS / "recettes" / f"{r['id']}.html").write_text(
            tmpl.render(titre=r["titre"], contenu_html=html), encoding="utf-8")

    # 10b. Injection du portail mot de passe sur toutes les pages HTML
    hash_mdp = hashlib.sha256(MOT_DE_PASSE.encode("utf-8")).hexdigest()
    gate = GATE_HTML.replace("__HASH__", hash_mdp)
    pages = list(DOCS.glob("*.html")) + list((DOCS / "recettes").glob("*.html"))
    for page in pages:
        contenu = page.read_text(encoding="utf-8")
        if "</head>" in contenu:
            page.write_text(contenu.replace("</head>", gate + "</head>", 1),
                            encoding="utf-8")
    print(f"Mot de passe ajouté sur {len(pages)} pages.")

    # 11. Service worker v7
    fichiers = (
        ["./index.html", "./style.css", "./menu.html",
         "./ingredients.html", "./courses.html"]
        + [f"./recettes/{r['id']}.html" for r in recettes]
    )
    (DOCS / "service-worker.js").write_text(_genere_sw(fichiers), encoding="utf-8")

    print(f"Site généré : {len(recettes)+4} pages HTML dans {DOCS}/")
    print("Prochaine étape : git add docs/ && git commit -m 'build' && git push")


def _genere_sw(fichiers):
    liste = ",\n    ".join(f'"{f}"' for f in fichiers)
    return f"""const CACHE = "recettes-v7";
const PRECACHE = [
    {liste}
];
self.addEventListener("install", e => {{
    e.waitUntil(caches.open(CACHE).then(c => c.addAll(PRECACHE)));
    self.skipWaiting();
}});
self.addEventListener("activate", e => {{
    e.waitUntil(caches.keys().then(keys =>
        Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))));
    self.clients.claim();
}});
self.addEventListener("fetch", e => {{
    e.respondWith(caches.match(e.request).then(cached => cached || fetch(e.request)));
}});
"""


if __name__ == "__main__":
    build()