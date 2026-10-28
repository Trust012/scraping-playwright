"""
Partie 2 : scraping d'une page à défilement infini (infinite scroll).

Site d'entraînement : https://quotes.toscrape.com/scroll
Il n'y a pas de bouton "Suivant" : de nouvelles citations se chargent
quand on descend en bas de la page (requêtes AJAX).

Ce que fait le script :
1. ouvre la page et attend les premières citations ;
2. descend en bas de la page ;
3. attend que de nouvelles citations apparaissent ;
4. recommence jusqu'à ce que plus rien ne se charge ;
5. extrait, nettoie et enregistre les données en CSV et JSON.

Lancement :
    python scrape_quotes_scroll.py
"""

import csv
import json

from playwright.sync_api import sync_playwright

URL = "https://quotes.toscrape.com/scroll"
MAX_DEFILEMENTS = 50        # sécurité : on ne défile jamais à l'infini
ATTENTE_MS = 1500           # temps laissé au site pour charger la suite
ESSAIS_SANS_NOUVEAU = 3     # on s'arrête après 3 défilements sans nouveauté
FICHIER_CSV = "citations_scroll.csv"
FICHIER_JSON = "citations_scroll.json"


def nettoyer(texte):
    return " ".join(texte.split()).strip("“”\"' ")


def nombre_de_citations(page):
    return page.locator(".quote").count()


def defiler_jusqu_au_bout(page):
    """Descend en bas de la page tant que de nouvelles citations arrivent."""
    essais_vides = 0
    avant = nombre_de_citations(page)

    for numero in range(1, MAX_DEFILEMENTS + 1):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(ATTENTE_MS)
        apres = nombre_de_citations(page)
        print(f"Défilement {numero} : {apres} citations chargées")

        if apres > avant:
            essais_vides = 0
            avant = apres
        else:
            essais_vides += 1
            if essais_vides >= ESSAIS_SANS_NOUVEAU:
                print("Plus rien ne se charge : fin de la page.")
                break


def extraire(page):
    resultats = []
    for bloc in page.locator(".quote").all():
        texte = bloc.locator(".text")
        auteur = bloc.locator(".author")
        resultats.append({
            "texte": nettoyer(texte.inner_text()) if texte.count() else "",
            "auteur": nettoyer(auteur.inner_text()) if auteur.count() else "",
            "tags": ", ".join(bloc.locator(".tags .tag").all_inner_texts()),
        })
    return resultats


def valider(citations):
    vues, propres = set(), []
    for c in citations:
        cle = (c["texte"], c["auteur"])
        if c["texte"] and c["auteur"] and cle not in vues:
            vues.add(cle)
            propres.append(c)
    return propres


def main():
    with sync_playwright() as p:
        navigateur = p.chromium.launch(headless=True)
        page = navigateur.new_page()
        page.goto(URL, timeout=30_000)
        page.wait_for_selector(".quote", timeout=15_000)

        defiler_jusqu_au_bout(page)
        citations = extraire(page)
        navigateur.close()

    propres = valider(citations)
    print(f"\n{len(citations)} citations lues, {len(propres)} gardées après nettoyage.")

    with open(FICHIER_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["texte", "auteur", "tags"])
        writer.writeheader()
        writer.writerows(propres)
    with open(FICHIER_JSON, "w", encoding="utf-8") as f:
        json.dump(propres, f, ensure_ascii=False, indent=2)

    print(f"Enregistré : {FICHIER_CSV} et {FICHIER_JSON}")


if __name__ == "__main__":
    main()