"""Parse le fichier markdown des recettes en une liste exploitable."""
from pathlib import Path
import re
import unicodedata


def _decoupe_sections(corps_md: str) -> dict:
    """
    Découpe le corps d'une recette en sections selon les titres ## .
    Renvoie un dict {nom_section_normalisee: texte_md_complet_avec_titre}.
    Les séparateurs --- internes à la recette sont supprimés.
    """
    # On retire les --- internes qui ne servaient qu'à la mise en page de la source.
    corps_md = re.sub(r"\n---\n", "\n\n", corps_md)

    # On split en gardant les titres ## comme délimiteurs.
    morceaux = re.split(r"(^##\s+.+$)", corps_md, flags=re.MULTILINE)

    sections = {}
    # morceaux[0] est ce qui précède le premier ## (souvent vide, parfois un sous-titre)
    preambule = morceaux[0].strip()
    if preambule:
        sections["_preambule"] = preambule

    # Les morceaux suivants vont par paires : titre, contenu, titre, contenu...
    for i in range(1, len(morceaux), 2):
        titre_section = morceaux[i].strip()
        contenu = morceaux[i + 1] if i + 1 < len(morceaux) else ""
        # Clé normalisée pour repérer la section indépendamment des accents/casse.
        cle = titre_section.lstrip("#").strip().lower()
        cle = unicodedata.normalize("NFD", cle)
        cle = "".join(c for c in cle if unicodedata.category(c) != "Mn")
        sections[cle] = titre_section + "\n" + contenu.rstrip() + "\n"

    return sections


def _reordonne(sections: dict) -> str:
    """
    Réassemble les sections dans l'ordre :
    préambule, ingrédients, commentaire, déroulé, puis le reste.
    """
    ordre_souhaite = ["ingredients", "commentaire", "deroule de la recette"]
    morceaux = []

    if "_preambule" in sections:
        morceaux.append(sections["_preambule"])

    cles_utilisees = {"_preambule"}
    for cle_voulue in ordre_souhaite:
        for cle in sections:
            if cle in cles_utilisees:
                continue
            if cle_voulue in cle or cle in cle_voulue:
                morceaux.append(sections[cle])
                cles_utilisees.add(cle)
                break

    # Sections restantes éventuelles
    for cle, contenu in sections.items():
        if cle not in cles_utilisees:
            morceaux.append(contenu)

    return "\n".join(morceaux)


def charger_recettes(chemin_md: str | Path) -> list[dict]:
    """
    Lit le fichier markdown et renvoie une liste de recettes triées.
    Chaque recette est un dict {id, titre, contenu_md}.
    """
    texte = Path(chemin_md).read_text(encoding="utf-8")

    # On split UNIQUEMENT sur les "---" qui séparent deux recettes,
    # c'est-à-dire ceux suivis d'un titre de niveau 1.
    blocs = re.split(r"\n---\n(?=\n?#\s)", texte)

    recettes = []
    titres_vus = set()

    for bloc in blocs:
        bloc = bloc.strip()
        if not bloc:
            continue

        match = re.match(r"^#\s+(.+?)\n(.*)", bloc, re.DOTALL)
        if not match:
            continue

        titre = match.group(1).strip()
        corps = match.group(2).strip()

        if not corps:
            continue
        if titre in titres_vus:
            continue
        titres_vus.add(titre)

        sections = _decoupe_sections(corps)
        corps_reordonne = _reordonne(sections)
        contenu_final = f"# {titre}\n\n{corps_reordonne}"

        recettes.append({
            "id": len(recettes),
            "titre": titre,
            "contenu_md": contenu_final,
        })

    def cle_tri(r):
        s = unicodedata.normalize("NFD", r["titre"].lower())
        return "".join(c for c in s if unicodedata.category(c) != "Mn")

    recettes.sort(key=cle_tri)
    for i, r in enumerate(recettes):
        r["id"] = i

    return recettes


if __name__ == "__main__":
    import sys
    chemin = sys.argv[1] if len(sys.argv) > 1 else "recettes.md"
    recettes = charger_recettes(chemin)
    print(f"{len(recettes)} recettes trouvées.\n")
    if recettes:
        print("=" * 60)
        print("Aperçu de la première recette :")
        print("=" * 60)
        print(recettes[0]["contenu_md"][:1500])
