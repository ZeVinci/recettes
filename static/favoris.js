/* favoris.js — gestion des recettes favorites.
 *
 * Les favoris sont identifiés par le slug de la recette (clé stable d'un build
 * à l'autre, identique à celle des avis Supabase) et persistés dans
 * localStorage. Ce module est partagé par le site statique (build.py) et la
 * preview Flask (liste.html).
 *
 * Pré-requis : chaque <li> de #liste-recettes porte data-slug et data-approuvee.
 * Usage      : poser les data-slug, puis appeler Favoris.init().
 * Évènement  : un CustomEvent "favoris:change" est émis sur document à chaque
 *              modification (la page s'en sert pour relancer son filtrage).
 */
(function (global) {
  "use strict";

  var CLE      = "favoris";        // tableau JSON de slugs
  var CLE_INIT = "favoris_init";   // drapeau : semis initial déjà effectué
  var seulementFavoris = false;    // état de la case « Favoris uniquement »

  function lire() {
    try { return new Set(JSON.parse(localStorage.getItem(CLE) || "[]")); }
    catch (e) { return new Set(); }
  }
  function ecrire(set) {
    localStorage.setItem(CLE, JSON.stringify(Array.from(set)));
  }
  var favoris = lire();

  function notifier() {
    document.dispatchEvent(new CustomEvent("favoris:change"));
  }

  function lis() {
    return Array.prototype.slice.call(
      document.querySelectorAll("#liste-recettes li[data-slug]"));
  }

  function titreDe(li) {
    if (li.dataset.title) return li.dataset.title.trim();
    var a = li.querySelector("a");
    if (a && a.childNodes.length) return (a.childNodes[0].textContent || "").trim();
    return li.dataset.slug;
  }

  /* Semis initial : une seule fois, depuis les recettes testées (data-approuvee).
     Le drapeau CLE_INIT garantit qu'on ne re-sème jamais — l'utilisateur reste
     ensuite seul maître de ses favoris. */
  function semer() {
    if (localStorage.getItem(CLE_INIT)) return;
    lis().forEach(function (li) {
      if (li.dataset.approuvee === "true") favoris.add(li.dataset.slug);
    });
    ecrire(favoris);
    localStorage.setItem(CLE_INIT, "1");
  }

  function estFavori(slug) { return favoris.has(slug); }

  function basculer(slug) {
    if (favoris.has(slug)) favoris.delete(slug); else favoris.add(slug);
    ecrire(favoris);
    majEtoiles();
    notifier();
  }

  function effacer() {
    if (!confirm("Effacer tous les favoris ?")) return;
    favoris = new Set();
    ecrire(favoris);                       // CLE_INIT conservé → pas de re-semis
    majEtoiles();
    notifier();
  }

  /* ── Étoiles : injection dans chaque <li> + mise à jour de l'état ── */
  function injecterEtoiles() {
    lis().forEach(function (li) {
      if (li.querySelector(".fav-star")) return;
      var b = document.createElement("button");
      b.type = "button";
      b.className = "fav-star";
      b.setAttribute("aria-label", "Favori");
      b.textContent = "\u2605";            // ★
      b.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();               // ne pas déclencher le mode sélection
        basculer(li.dataset.slug);
      });
      li.appendChild(b);
    });
    majEtoiles();
  }
  function majEtoiles() {
    lis().forEach(function (li) {
      var b = li.querySelector(".fav-star");
      if (!b) return;
      var on = favoris.has(li.dataset.slug);
      b.classList.toggle("on", on);
      b.title = on ? "Retirer des favoris" : "Ajouter aux favoris";
    });
  }

  /* ── Export / import ── */
  function exporter() {
    var titres = {};
    lis().forEach(function (li) { titres[li.dataset.slug] = titreDe(li); });
    var data = {
      version:    1,
      exporte_le: new Date().toISOString().slice(0, 10),
      favoris:    Array.from(favoris).map(function (slug) {
        return { slug: slug, titre: titres[slug] || slug };
      })
    };
    var blob = new Blob([JSON.stringify(data, null, 2)],
                        { type: "application/json" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = "favoris-recettes.json";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function importer(fichier) {
    var reader = new FileReader();
    reader.onload = function () {
      var slugs;
      try {
        var obj   = JSON.parse(reader.result);
        var liste = Array.isArray(obj) ? obj : obj.favoris;
        slugs = (liste || []).map(function (x) {
          return typeof x === "string" ? x : (x && x.slug);
        }).filter(Boolean);
      } catch (e) {
        alert("Fichier de favoris illisible.");
        return;
      }
      favoris = new Set(slugs);            // remplacement (choix retenu)
      ecrire(favoris);
      localStorage.setItem(CLE_INIT, "1"); // évite un re-semis ultérieur
      majEtoiles();
      notifier();
      alert(favoris.size + " favori(s) importé(s).");
    };
    reader.readAsText(fichier);
  }

  /* ── Barre de contrôle injectée dans #fav-controls ── */
  function injecterControles() {
    var hote = document.getElementById("fav-controls");
    if (!hote || hote.dataset.pret) return;
    hote.dataset.pret = "1";
    hote.innerHTML =
      '<label class="fav-only"><input type="checkbox" id="fav-only-cb">' +
      ' \u2605 Favoris uniquement</label>' +
      '<span class="fav-actions">' +
      '<button type="button" class="fav-btn" id="fav-export">Exporter</button>' +
      '<button type="button" class="fav-btn" id="fav-import">Importer</button>' +
      '<button type="button" class="fav-btn" id="fav-clear">Effacer</button>' +
      '</span>' +
      '<input type="file" id="fav-file" accept="application/json,.json" hidden>';

    document.getElementById("fav-only-cb").addEventListener("change", function (e) {
      seulementFavoris = e.target.checked;
      notifier();
    });
    document.getElementById("fav-export").addEventListener("click", exporter);
    document.getElementById("fav-clear").addEventListener("click", effacer);

    var file = document.getElementById("fav-file");
    document.getElementById("fav-import").addEventListener("click", function () {
      file.value = "";
      file.click();
    });
    file.addEventListener("change", function () {
      if (file.files && file.files[0]) importer(file.files[0]);
    });
  }

  function init() {
    semer();
    injecterControles();
    injecterEtoiles();
  }

  global.Favoris = {
    init:      init,
    estFavori: estFavori,
    seulement: function () { return seulementFavoris; }
  };
})(window);
