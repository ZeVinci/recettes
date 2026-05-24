"""Parse le fichier markdown des recettes en une liste exploitable."""
from pathlib import Path
import re
import unicodedata


# ── Utilitaires ────────────────────────────────────────────────────────────────

def _normaliser(texte: str) -> str:
    s = unicodedata.normalize("NFD", texte.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


# ── Fractions ─────────────────────────────────────────────────────────────────

_FRACS = {"½": 0.5, "¼": 0.25, "¾": 0.75, "⅓": 1/3, "⅔": 2/3, "⅛": 0.125}

def _parse_nombre(s: str) -> float | None:
    s = s.strip()
    if s in _FRACS:
        return _FRACS[s]
    m = re.match(r"^(\d+)\s*([½¼¾⅓⅔⅛])$", s)
    if m:
        return int(m.group(1)) + _FRACS[m.group(2)]
    m = re.match(r"^(\d+)/(\d+)$", s)
    if m:
        return int(m.group(1)) / int(m.group(2))
    m = re.match(r"^(\d+(?:[.,]\d+)?)$", s)
    if m:
        return float(m.group(1).replace(",", "."))
    return None


# ── Extraction des quantités ───────────────────────────────────────────────────

_RE_FRAC_PREFIX = re.compile(
    r"^([¼½¾⅓⅔⅛]|\d+/\d+)\s+de\s+", re.IGNORECASE
)

_RE_QTE = re.compile(
    r"^(?P<qte>[¼½¾⅓⅔⅛]|\d+(?:[.,]\d+)?(?:\s*[½¼¾⅓⅔⅛])?|\d+/\d+)\s*"
    r"(?P<unite>"
    r"g|kg|cl|ml|l(?=\s)|"
    r"cuil(?:lerée?s?)?\.?\s*[àa]\s*(?:soupe?|café|c\.?)|"
    r"cuillerée?s?\s*[àa]\s*(?:soupe?|café)|"
    r"c\.\s*[àa]\s*[cs]\.?|"
    r"pincée?s?|gousse?s?|tranche?s?|feuille?s?|"
    r"brin?s?|tige?s?|botte?s?|filet?s?|noix|sachet?s?"
    r")?\s*"
    r"(?:de\s+|d[eu]\s+|[àa]\s+)?"
    r"(?P<nom>.+)$",
    re.IGNORECASE,
)


def _normaliser_unite(u: str | None) -> str | None:
    if not u:
        return None
    u = u.strip().lower()
    if re.search(r"soupe", u):   return "cuil. à soupe"
    if re.search(r"caf",  u):    return "cuil. à café"
    if re.search(r"cuil|c\.", u): return "cuil."
    if u.startswith("pinc"):     return "pincée"
    if u.startswith("gouss"):    return "gousse"
    if u.startswith("brin"):     return "brin"
    return u


def parse_ligne_ingredient(ligne: str) -> dict:
    ligne_brute = ligne.lstrip("- ").strip()
    s = re.sub(r"\*([^*]+)\*", r"\1", ligne_brute)
    s = s.split("(")[0].strip()
    s = s.split(",")[0].strip()

    m_frac = _RE_FRAC_PREFIX.match(s)
    frac_mult = None
    if m_frac:
        frac_mult = _parse_nombre(m_frac.group(1))
        s = s[m_frac.end():]

    m = _RE_QTE.match(s)
    if not m:
        return {"nom": s.lower().strip(), "qte": None,
                "unite": None, "ligne_brute": ligne_brute}

    qte   = _parse_nombre(m.group("qte").strip())
    unite = _normaliser_unite(m.group("unite"))
    nom   = m.group("nom").strip().lower()

    if frac_mult is not None and qte is not None:
        qte = frac_mult * qte
    elif frac_mult is not None:
        qte = frac_mult

    if unite == "kg" and qte is not None:
        qte *= 1000; unite = "g"
    if unite == "l" and qte is not None:
        qte *= 100;  unite = "cl"
    if unite == "ml" and qte is not None:
        qte /= 10;   unite = "cl"

    return {"nom": nom, "qte": qte, "unite": unite, "ligne_brute": ligne_brute}


# ── Extraction du nombre de personnes ─────────────────────────────────────────

_RE_PERSONNES = re.compile(
    r"[Pp]our\s+(\d+)(?:\s*[àa]\s*(\d+))?\s*personnes?", re.IGNORECASE
)

def _extrait_personnes(contenu_md: str) -> int:
    m = _RE_PERSONNES.search(contenu_md)
    if not m:
        return 4
    n1 = int(m.group(1))
    n2 = int(m.group(2)) if m.group(2) else None
    return (n1 + n2) // 2 if n2 else n1


# ── Découpe en sections ────────────────────────────────────────────────────────

def _decoupe_sections(corps_md: str) -> dict:
    corps_md = re.sub(r"\n---\n", "\n\n", corps_md)
    morceaux = re.split(r"(^##\s+.+$)", corps_md, flags=re.MULTILINE)
    sections = {}
    preambule = morceaux[0].strip()
    if preambule:
        sections["_preambule"] = preambule
    for i in range(1, len(morceaux), 2):
        titre_section = morceaux[i].strip()
        contenu = morceaux[i + 1] if i + 1 < len(morceaux) else ""
        cle = _normaliser(titre_section.lstrip("#").strip())
        sections[cle] = titre_section + "\n" + contenu.rstrip() + "\n"
    return sections


# ── Extraction des catégories ──────────────────────────────────────────────────

def _extrait_categories(sections: dict) -> list[str]:
    for cle, contenu in sections.items():
        if "categorie" in cle:
            lignes = [l.strip() for l in contenu.splitlines()
                      if l.strip() and not l.startswith("##")]
            if lignes:
                return [t.strip() for t in lignes[0].split(".") if t.strip()]
    return []


# ── Détection approuvée / bibliothèque ────────────────────────────────────────

def _extrait_approuvee(categories: list[str]) -> bool:
    """
    Retourne True si la recette est approuvée (pas de 'Pas testé' dans les catégories).
    Retourne False si la recette est dans la bibliothèque ('Pas testé' présent).
    """
    return not any(_normaliser(c) == _normaliser("Pas testé") for c in categories)


# ── Extraction des ingrédients curés ──────────────────────────────────────────

def _extrait_ingredients_cures(sections: dict) -> list[str] | None:
    for cle, contenu in sections.items():
        if "noms ingredients" in cle or "noms ingr" in cle:
            lignes = [l.strip() for l in contenu.splitlines()
                      if l.strip() and not l.startswith("##")]
            if lignes:
                return [t.strip() for t in lignes[0].split(".") if t.strip()]
    return None


# ── Extraction des ingrédients avec quantités ─────────────────────────────────

def _extrait_ingredients_avec_qtes(sections: dict) -> list[dict]:
    for cle, contenu in sections.items():
        if "ingredients" in cle and "noms" not in cle:
            result = []
            for ligne in contenu.splitlines():
                if not ligne.startswith("- "):
                    continue
                parsed = parse_ligne_ingredient(ligne)
                if parsed["nom"] and len(parsed["nom"]) > 2:
                    result.append(parsed)
            return result
    return []


# ── Extraction automatique (fallback) ─────────────────────────────────────────

_RE_QUANTITE_AUTO = re.compile(
    r"""^[\d½¼¾⅓⅔\s,./]+\s*
        (?:g|kg|cl|ml|l|litre?s?|
           cuil(?:lerée?s?)?\.?\s*[àa]\s*(?:soupe?|café|c\.?)|
           cuillerée?s?\s*[àa]\s*(?:soupe?|café)|
           pincée?s?|brin?s?|gousse?s?|tranche?s?|
           feuille?s?|tige?s?|botte?s?|morceau?x?|filet?s?|noix)
        \s+(?:de\s+|d[eu]\s+|[àa]\s+)""",
    re.VERBOSE | re.IGNORECASE,
)
_RE_NOMBRE_AUTO = re.compile(r"^[\d½¼¾⅓⅔\s,./]+\s+")


def _extraire_nom_auto(ligne: str) -> str | None:
    ligne = re.sub(r"\*([^*]+)\*", r"\1", ligne)
    ligne = ligne.split(",")[0].split("(")[0].strip()
    ligne = _RE_QUANTITE_AUTO.sub("", ligne).strip()
    ligne = _RE_NOMBRE_AUTO.sub("", ligne).strip()
    ligne = ligne.lstrip("''-").strip().lower()
    if len(ligne) < 3 or ligne[0].isdigit():
        return None
    if re.match(r"^(soupe|café|c\.) (de |d')", ligne):
        return None
    return ligne


def _extrait_ingredients_auto(sections: dict) -> list[str]:
    for cle, contenu in sections.items():
        if "ingredients" in cle and "noms" not in cle:
            noms = []
            for ligne in contenu.splitlines():
                if not ligne.startswith("- "):
                    continue
                nom = _extraire_nom_auto(ligne[2:].strip())
                if nom and nom not in noms:
                    noms.append(nom)
            return noms
    return []


# ── Réordonnancement des sections ─────────────────────────────────────────────

def _reordonne(sections: dict) -> str:
    ordre = ["ingredients", "commentaire", "deroule de la recette"]
    morceaux = []
    if "_preambule" in sections:
        morceaux.append(sections["_preambule"])
    utilisees = {"_preambule"}
    for cle_voulue in ordre:
        for cle in sections:
            if cle in utilisees:
                continue
            if cle_voulue in cle or cle in cle_voulue:
                morceaux.append(sections[cle])
                utilisees.add(cle)
                break
    EXCLUES = {"categorie", "noms ingredients", "noms ingr"}
    for cle, contenu in sections.items():
        if cle in utilisees:
            continue
        if any(ex in cle for ex in EXCLUES):
            continue
        morceaux.append(contenu)
    return "\n".join(morceaux)


# ── Point d'entrée public ──────────────────────────────────────────────────────

def charger_recettes(chemin_md: str | Path) -> list[dict]:
    """
    Retourne une liste de dicts :
      id              : int
      titre           : str
      tags            : list[str]
      approuvee       : bool   — True = recette éprouvée, False = bibliothèque
      personnes       : int
      ingredients     : list[str]   — mots-clés pour le filtre frigo
      ingredients_qte : list[dict]  — [{nom, qte, unite, ligne_brute}]
      source_ing      : str         — "cure" | "auto"
      contenu_md      : str
    """
    texte = Path(chemin_md).read_text(encoding="utf-8")
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
        if not corps or titre in titres_vus:
            continue
        titres_vus.add(titre)

        sections  = _decoupe_sections(corps)
        tags      = _extrait_categories(sections)
        approuvee = _extrait_approuvee(tags)
        personnes = _extrait_personnes(corps)

        # Ingrédients curés (filtre frigo)
        ingredients_cures = _extrait_ingredients_cures(sections)
        if ingredients_cures is not None:
            ingredients = ingredients_cures
            source_ing  = "cure"
        else:
            ingredients = _extrait_ingredients_auto(sections)
            source_ing  = "auto"

        # Ingrédients avec quantités (liste de courses)
        ingredients_qte = _extrait_ingredients_avec_qtes(sections)

        corps_reordonne = _reordonne(sections)
        contenu_final   = f"# {titre}\n\n{corps_reordonne}"

        recettes.append({
            "id":              len(recettes),
            "titre":           titre,
            "tags":            tags,
            "approuvee":       approuvee,
            "personnes":       personnes,
            "ingredients":     ingredients,
            "ingredients_qte": ingredients_qte,
            "source_ing":      source_ing,
            "contenu_md":      contenu_final,
        })

    recettes.sort(key=lambda r: _normaliser(r["titre"]))
    for i, r in enumerate(recettes):
        r["id"] = i

    return recettes


# ── Test rapide ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    chemin = sys.argv[1] if len(sys.argv) > 1 else "recettes.md"
    recettes = charger_recettes(chemin)
    nb_app = sum(1 for r in recettes if r["approuvee"])
    nb_bib = sum(1 for r in recettes if not r["approuvee"])
    nb_cures = sum(1 for r in recettes if r["source_ing"] == "cure")
    print(f"{len(recettes)} recettes — {nb_app} approuvées, {nb_bib} bibliothèque, {nb_cures} curées")
    print()
    for r in recettes[:3]:
        print(f"  [{'✓' if r['approuvee'] else '📚'}] {r['titre']}")
        print(f"       tags: {r['tags']}")
        print(f"       ing:  {r['ingredients'][:4]}")
        print()