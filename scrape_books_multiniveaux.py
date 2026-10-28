"""
Partie 3 : scraping d'un site à plusieurs niveaux.

Site d'entraînement : https://books.toscrape.com (fausse librairie)

Les 3 niveaux :
  Niveau 1 : la page d'accueil      -> liste des catégories
  Niveau 2 : une page de catégorie  -> liste des livres (sur plusieurs pages)
  Niveau 3 : la fiche d'un livre    -> prix, stock, note, UPC, description

Ce que fait le script :
1. récupère les catégories ;
2. pour chaque catégorie choisie, parcourt toutes ses pages de livres ;
3. ouvre la fiche de chaque livre et en extrait les détails ;
4. réessaie en cas d'échec, et note les erreurs au lieu de s'arrêter ;
5. nettoie et convertit les données (prix en nombre, note en chiffre, stock) ;
6. enregistre en CSV et JSON, plus un fichier d'erreurs s'il y en a.

Lancement :
    python scrape_books_multiniveaux.py
"""

import csv
import json
import re
import time
from urllib.parse import urljoin

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

URL_ACCUEIL = "https://books.toscrape.com/"
CATEGORIES_VOULUES = ["Travel", "Poetry", "Science"]   # [] = toutes les catégories
MAX_LIVRES_PAR_CATEGORIE = 50     # limite pour garder des tests rapides
ESSAIS_MAX = 3
PAUSE_ENTRE_PAGES = 0.5           # politesse : on ne surcharge pas le site
FICHIER_CSV = "livres.csv"
FICHIER_JSON = "livres.json"
FICHIER_ERREURS = "erreurs.json"

NOTES = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def ouvrir(page, url, selecteur):
    """Ouvre une URL et attend un élément. Réessaie avant d'abandonner."""
    for essai in range(1, ESSAIS_MAX + 1):
        try:
            page.goto(url, timeout=30_000)
            page.wait_for_selector(selecteur, timeout=15_000)
            time.sleep(PAUSE_ENTRE_PAGES)
            return True
        except PlaywrightError:
            print(f"    Essai {essai}/{ESSAIS_MAX} échoué : {url}")
            time.sleep(2 * essai)
    return False


# ----- Niveau 1 : catégories -------------------------------------------------
def lire_categories(page):
    categories = {}
    for lien in page.locator(".side_categories ul li ul li a").all():
        nom = " ".join(lien.inner_text().split())
        categories[nom] = urljoin(page.url, lien.get_attribute("href"))
    return categories


# ----- Niveau 2 : liste des livres d'une catégorie (avec pagination) ---------
def lire_liens_livres(page, url_categorie):
    liens = []
    url = url_categorie
    while url and len(liens) < MAX_LIVRES_PAR_CATEGORIE:
        if not ouvrir(page, url, "article.product_pod"):
            break
        for a in page.locator("article.product_pod h3 a").all():
            liens.append(urljoin(page.url, a.get_attribute("href")))
        suivant = page.locator("li.next a")
        url = urljoin(page.url, suivant.get_attribute("href")) if suivant.count() else None
    return liens[:MAX_LIVRES_PAR_CATEGORIE]


# ----- Niveau 3 : fiche d'un livre -------------------------------------------
def texte(page, selecteur):
    element = page.locator(selecteur)
    return " ".join(element.first.inner_text().split()) if element.count() else ""


def lire_fiche(page, url, categorie):
    infos_tableau = {}
    for ligne in page.locator("table.table-striped tr").all():
        cle = " ".join(ligne.locator("th").inner_text().split())
        valeur = " ".join(ligne.locator("td").inner_text().split())
        infos_tableau[cle] = valeur

    classes = page.locator("p.star-rating").first.get_attribute("class") or ""
    note = next((v for k, v in NOTES.items() if k in classes.split()), None)

    prix_texte = texte(page, ".product_main p.price_color")
    prix = re.search(r"[\d.]+", prix_texte)

    stock_texte = texte(page, ".product_main p.availability")
    stock = re.search(r"\d+", stock_texte)

    return {
        "categorie": categorie,
        "titre": texte(page, ".product_main h1"),
        "prix_gbp": float(prix.group()) if prix else None,
        "en_stock": "In stock" in stock_texte,
        "quantite_stock": int(stock.group()) if stock else 0,
        "note_sur_5": note,
        "upc": infos_tableau.get("UPC", ""),
        "description": texte(page, "#product_description ~ p"),
        "url": url,
    }


def valider(livres):
    """Écarte les fiches sans titre ou sans prix, et les doublons (même UPC)."""
    vus, propres = set(), []
    for livre in livres:
        if not livre["titre"] or livre["prix_gbp"] is None:
            continue
        cle = livre["upc"] or livre["url"]
        if cle in vus:
            continue
        vus.add(cle)
        propres.append(livre)
    return propres


def main():
    livres, erreurs = [], []
    with sync_playwright() as p:
        navigateur = p.chromium.launch(headless=True)
        page = navigateur.new_page()

        if not ouvrir(page, URL_ACCUEIL, ".side_categories"):
            print("Impossible d'ouvrir la page d'accueil.")
            return
        categories = lire_categories(page)
        print(f"{len(categories)} catégories trouvées.")

        choisies = {n: u for n, u in categories.items()
                    if not CATEGORIES_VOULUES or n in CATEGORIES_VOULUES}

        for nom, url_categorie in choisies.items():
            liens = lire_liens_livres(page, url_categorie)
            print(f"\n[{nom}] {len(liens)} livres à visiter")
            for i, url_livre in enumerate(liens, 1):
                if not ouvrir(page, url_livre, ".product_main"):
                    erreurs.append({"categorie": nom, "url": url_livre,
                                    "raison": "page non chargée"})
                    continue
                try:
                    livre = lire_fiche(page, url_livre, nom)
                    livres.append(livre)
                    print(f"  {i}/{len(liens)} {livre['titre'][:60]}")
                except PlaywrightError as e:
                    erreurs.append({"categorie": nom, "url": url_livre,
                                    "raison": str(e)[:200]})

        navigateur.close()

    propres = valider(livres)
    print(f"\n{len(livres)} fiches lues, {len(propres)} gardées, {len(erreurs)} erreurs.")

    if propres:
        with open(FICHIER_CSV, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=propres[0].keys())
            writer.writeheader()
            writer.writerows(propres)
        with open(FICHIER_JSON, "w", encoding="utf-8") as f:
            json.dump(propres, f, ensure_ascii=False, indent=2)
        print(f"Enregistré : {FICHIER_CSV} et {FICHIER_JSON}")
    if erreurs:
        with open(FICHIER_ERREURS, "w", encoding="utf-8") as f:
            json.dump(erreurs, f, ensure_ascii=False, indent=2)
        print(f"Erreurs détaillées dans : {FICHIER_ERREURS}")


if __name__ == "__main__":
    main()