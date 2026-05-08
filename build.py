"""
build.py — Génère le site statique dans le dossier docs/.

Usage : python build.py
Le dossier docs/ est ensuite poussé sur GitHub, et GitHub Pages le sert.

Dépendances : pip install markdown jinja2
"""
import shutil
from pathlib import Path
import markdown as md_lib
from jinja2 import Environment, BaseLoader
from parser import charger_recettes

# ── Chemins ────────────────────────────────────────────────────────────────────
RECETTES_MD = Path("recettes.md")
STATIC_SRC  = Path("static")
DOCS        = Path("docs")          # dossier servi par GitHub Pages

# ── Templates HTML inline (on n'a plus besoin de Flask) ────────────────────────
# Le chemin vers style.css est relatif, donc les pages recette/ doivent
# remonter d'un niveau avec "../style.css".

TMPL_LISTE = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mes recettes</title>
    <link rel="stylesheet" href="style.css">
    <link rel="manifest" href="manifest.json">
    <meta name="theme-color" content="#8b4513">
</head>
<body>
    <header>
        <h1>Mes recettes</h1>
        <input type="text" id="recherche" placeholder="Rechercher…" autocomplete="off">
    </header>

    <ul id="liste-recettes">
        {% for r in recettes %}
        <li><a href="recettes/{{ r.id }}.html">{{ r.titre }}</a></li>
        {% endfor %}
    </ul>

    <p class="compteur">{{ recettes|length }} recettes</p>

    <script>
        const champ = document.getElementById('recherche');
        const items = document.querySelectorAll('#liste-recettes li');
        champ.addEventListener('input', () => {
            const q = champ.value.toLowerCase().trim();
            items.forEach(li => {
                li.style.display = li.textContent.toLowerCase().includes(q) ? '' : 'none';
            });
        });
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('service-worker.js');
        }
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
    <meta name="theme-color" content="#8b4513">
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

# ── Génération ─────────────────────────────────────────────────────────────────
def build():
    # 1. Table rase du dossier docs/ (pour ne pas garder d'anciennes recettes)
    if DOCS.exists():
        import time
        for tentative in range(5):
            try:
                shutil.rmtree(DOCS)
                break
            except PermissionError:
                time.sleep(0.5)
        else:
            # Si ça échoue encore, on vide le contenu sans supprimer le dossier
            for f in DOCS.rglob("*"):
                if f.is_file():
                    f.unlink(missing_ok=True)
    DOCS.mkdir(exist_ok=True)
    (DOCS / "recettes").mkdir(exist_ok=True)

    # 2. Copie des fichiers statiques
    for f in STATIC_SRC.iterdir():
        shutil.copy(f, DOCS / f.name)

    # 3. Chargement et parsing des recettes
    recettes = charger_recettes(RECETTES_MD)
    print(f"{len(recettes)} recettes chargées.")

    env = Environment(loader=BaseLoader())

    # 4. Génération de l'index
    tmpl = env.from_string(TMPL_LISTE)
    (DOCS / "index.html").write_text(
        tmpl.render(recettes=recettes), encoding="utf-8"
    )

    # 5. Génération d'une page par recette
    tmpl = env.from_string(TMPL_RECETTE)
    for r in recettes:
        html = md_lib.markdown(r["contenu_md"], extensions=["extra", "sane_lists"])
        page = tmpl.render(titre=r["titre"], contenu_html=html)
        (DOCS / "recettes" / f"{r['id']}.html").write_text(page, encoding="utf-8")

    # 6. Service worker : on met à jour la liste des fichiers à précacher
    #    pour que TOUTES les recettes soient disponibles hors ligne dès l'ouverture.
    fichiers_a_cacher = (
        ["./index.html", "./style.css"]
        + [f"./recettes/{r['id']}.html" for r in recettes]
    )
    sw = _genere_service_worker(fichiers_a_cacher)
    (DOCS / "service-worker.js").write_text(sw, encoding="utf-8")

    print(f"Site généré dans {DOCS}/ ({len(recettes) + 1} pages HTML).")
    print("Prochaine étape : git add docs/ && git commit -m 'build' && git push")


def _genere_service_worker(fichiers: list[str]) -> str:
    """
    Génère un service worker qui précache TOUTES les recettes au premier chargement.
    Ainsi, même sans connexion, toutes les recettes sont disponibles.
    """
    liste = ",\n    ".join(f'"{f}"' for f in fichiers)
    return f"""// Service worker — généré automatiquement par build.py
const CACHE = "recettes-v1";
const PRECACHE = [
    {liste}
];

self.addEventListener("install", e => {{
    e.waitUntil(
        caches.open(CACHE).then(c => c.addAll(PRECACHE))
    );
    self.skipWaiting();
}});

self.addEventListener("activate", e => {{
    e.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
        )
    );
    self.clients.claim();
}});

self.addEventListener("fetch", e => {{
    e.respondWith(
        caches.match(e.request).then(cached => cached || fetch(e.request))
    );
}});
"""


if __name__ == "__main__":
    build()
