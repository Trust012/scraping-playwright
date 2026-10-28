"""
Partie 1 : scraping d'un site rendu en JavaScript, avec pagination.

Site d'entraînement : https://quotes.toscrape.com/js/
Les citations n'existent pas dans le HTML de départ : c'est du JavaScript
qui les ajoute. BeautifulSoup seul ne les voit donc pas, mais Playwright,
qui pilote un vrai navigateur, les voit.

Ce que fait le script :
1. ouvre chaque page dans un navigateur Chromium invisible ;
2. attend que le JavaScript ait affiché les citations ;
3. extrait texte, auteur et tags ;
4. clique sur "Next" jusqu'à la dernière page ;
5. nettoie, supprime les doublons, vérifie les données ;
6. enregistre le résultat en CSV et en JSON.

Installation (une seule fois) :
    pip install playwright
    playwright install chromium

Lancement :
    python scrape_quotes_js.py
"""

import csv
import json
import time
from urllib.parse import urljoin

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

URL_DEPART = "https://quotes.toscrape.com/js/"
MAX_PAGES = 20            # sécurité : on ne boucle jamais à l'infini
ESSAIS_MAX = 3            # nombre de tentatives si une page ne charge pas
FICHIER_CSV = "citations.csv"
FICHIER_JSON = "citations.json"


def charger_page(page, url):
    """Ouvre l'URL et attend les citations. Réessaie en cas d'échec."""
    for essai in range(1, ESSAIS_MAX + 1):
        try:
            page.goto(url, timeout=30_000)
            page.wait_for_selector(".quote", timeout=15_000)
            return True
        except PlaywrightTimeout:
            print(f"  Essai {essai}/{ESSAIS_MAX} échoué pour {url}")
            time.sleep(2 * essai)          # on attend un peu plus à chaque fois
    return False


def nettoyer(texte):
    """Enlève les espaces en trop et les guillemets décoratifs “ ”."""
    return " ".join(texte.split()).strip("“”\"' ")


def extraire_citations(page):
    """Lit toutes les citations affichées sur la page."""
    resultats = []
    for bloc in page.query_selector_all(".quote"):
        texte = bloc.query_selector(".text")
        auteur = bloc.query_selector(".author")
        tags = [t.inner_text() for t in bloc.query_selector_all(".tags .tag")]
        resultats.append({
            "texte": nettoyer(texte.inner_text()) if texte else "",
            "auteur": nettoyer(auteur.inner_text()) if auteur else "",
            "tags": ", ".join(tags),
        })
    return resultats


def valider(citations):
    """Garde les lignes complètes et supprime les doublons."""
    vues = set()
    propres = []
    for c in citations:
        if not c["texte"] or not c["auteur"]:
            continue                       # ligne incomplète : on l'écarte
        cle = (c["texte"], c["auteur"])
        if cle in vues:
            continue                       # doublon
        vues.add(cle)
        propres.append(c)
    return propres


def main():
    toutes = []
    with sync_playwright() as p:
        navigateur = p.chromium.launch(headless=True)
        page = navigateur.new_page()
        url = URL_DEPART

        for numero in range(1, MAX_PAGES + 1):
            print(f"Page {numero} : {url}")
            if not charger_page(page, url):
                print("  Page impossible à charger, arrêt.")
                break

            citations = extraire_citations(page)
            print(f"  {len(citations)} citations trouvées")
            toutes.extend(citations)

            suivant = page.query_selector("li.next > a")
            if not suivant:
                print("Dernière page atteinte.")
                break
            url = urljoin(page.url, suivant.get_attribute("href"))

        navigateur.close()

    propres = valider(toutes)
    print(f"\n{len(toutes)} citations lues, {len(propres)} gardées après nettoyage.")

    with open(FICHIER_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["texte", "auteur", "tags"])
        writer.writeheader()
        writer.writerows(propres)
    with open(FICHIER_JSON, "w", encoding="utf-8") as f:
        json.dump(propres, f, ensure_ascii=False, indent=2)

    print(f"Enregistré : {FICHIER_CSV} et {FICHIER_JSON}")


if __name__ == "__main__":
    main()