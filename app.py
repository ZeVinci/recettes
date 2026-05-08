"""Mini-serveur Flask pour afficher les recettes."""
from flask import Flask, render_template, abort, send_from_directory
import markdown as md_lib
from parser import charger_recettes

app = Flask(__name__)

# On charge les recettes une fois au démarrage (rapide, pas besoin de relire
# le fichier à chaque requête). Si tu modifies le .md, redémarre le serveur.
RECETTES = charger_recettes("recettes.md")


@app.route("/")
def liste():
    """Page d'accueil : liste des titres."""
    return render_template("liste.html", recettes=RECETTES)


@app.route("/recette/<int:recette_id>")
def recette(recette_id: int):
    """Affichage d'une recette individuelle."""
    if recette_id < 0 or recette_id >= len(RECETTES):
        abort(404)
    r = RECETTES[recette_id]
    # Conversion markdown → HTML. L'extension "extra" gère les listes,
    # les emphases, etc. L'extension "sane_lists" évite les surprises sur
    # les listes numérotées.
    html = md_lib.markdown(r["contenu_md"], extensions=["extra", "sane_lists"])
    return render_template("recette.html", titre=r["titre"], contenu_html=html)


# Routes pour servir le manifest et le service worker depuis la racine
# (requis pour que la PWA fonctionne correctement).
@app.route("/manifest.json")
def manifest():
    return send_from_directory("static", "manifest.json", mimetype="application/json")


@app.route("/service-worker.js")
def service_worker():
    return send_from_directory("static", "service-worker.js", mimetype="application/javascript")


if __name__ == "__main__":
    # host="0.0.0.0" pour rendre le serveur accessible depuis ton téléphone
    # sur le même Wi-Fi. Si tu ne veux que ton ordi, mets "127.0.0.1".
    app.run(host="0.0.0.0", port=5000, debug=True)
