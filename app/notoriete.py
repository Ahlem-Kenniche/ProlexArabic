# -*- coding: utf-8 -*-
"""
Module de calcul de l'indice de notoriété temporelle.

Implémente la méthode SAW (Simple Additive Weighting) avec pondération
par entropie de Shannon, basée sur 5 critères Wikipedia :
  1. Nombre de contributeurs
  2. Taille de l'article
  3. Liens internes (backlinks)
  4. Liens externes
  5. Nombre de visites (pondéré temporellement)

Usage :
    from notoriete import calculer_notoriete
    calculer_notoriete("pol", "pl")   # polonais
    calculer_notoriete("srp", "sr")   # serbe
"""

import logging
import math
import os
import sqlite3
import time

import numpy as np
import requests

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.environ.get(
    "PROLEXARABIC_DB",
    os.path.join(PROJECT_ROOT, "data_sample", "prolexbase_sample.db"),
)

log = logging.getLogger(__name__)

_UA = "ProlexArabicBot/1.0 (university research project)"


# ═══════════════════════════════════════════════════════════════════════════════
# 1. FONCTIONS D'APPEL API WIKIPEDIA
# ═══════════════════════════════════════════════════════════════════════════════

def get_nbr_contributors(wiki_domain, name):
    """Nombre de contributeurs d'un article Wikipedia."""
    url = (
        f"https://{wiki_domain}.wikipedia.org/w/api.php"
        f"?action=query&titles={name}&prop=contributors"
        f"&pclimit=max&format=json&nonredirects&rawcontinue"
    )
    try:
        r = requests.get(url, headers={"User-Agent": _UA}, timeout=15)
        pages = r.json()["query"]["pages"]
        page = pages[next(iter(pages))]
        return len(page.get("contributors", []))
    except Exception:
        return 0


def get_size(wiki_domain, name):
    """Taille (octets) de la dernière révision d'un article."""
    url = (
        f"https://{wiki_domain}.wikipedia.org/w/api.php"
        f"?action=query&prop=revisions&rvprop=size&format=json"
        f"&titles={name}&redirects"
    )
    try:
        r = requests.get(url, headers={"User-Agent": _UA}, timeout=15)
        pages = r.json()["query"]["pages"]
        page = pages[next(iter(pages))]
        return page["revisions"][0]["size"]
    except Exception:
        return 0


def get_nbr_int_links(wiki_domain, name):
    """Nombre de liens internes (backlinks) vers un article."""
    url = (
        f"https://{wiki_domain}.wikipedia.org/w/api.php"
        f"?action=query&list=backlinks&bllimit=max&bltitle={name}"
        f"&blfilterredir=nonredirects&format=json&rawcontinue"
    )
    try:
        r = requests.get(url, headers={"User-Agent": _UA}, timeout=15)
        return len(r.json()["query"]["backlinks"])
    except Exception:
        return 0


def get_nbr_ext_links(wiki_domain, name):
    """Nombre de liens externes dans un article."""
    url = (
        f"https://{wiki_domain}.wikipedia.org/w/api.php"
        f"?action=query&titles={name}&prop=extlinks&format=json&ellimit=max"
    )
    try:
        r = requests.get(url, headers={"User-Agent": _UA}, timeout=15)
        pages = r.json()["query"]["pages"]
        page = pages[next(iter(pages))]
        return len(page.get("extlinks", []))
    except Exception:
        return 0


def get_nbr_visite(wiki_domain, name):
    """Nombre de visites pondéré temporellement (2015-2024)."""
    url = (
        f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
        f"/{wiki_domain}.wikipedia/all-access/all-agents/{name}"
        f"/monthly/20150801/20240101"
    )
    try:
        r = requests.get(url, headers={"User-Agent": _UA}, timeout=15)
        items = r.json()["items"]
        visits = 0.0
        n = len(items)
        for idx, item in enumerate(items, start=1):
            visits += item["views"] * (idx / n)
        return visits
    except Exception:
        return 0


# ═══════════════════════════════════════════════════════════════════════════════
# 2. COLLECTE DES DONNÉES POUR UNE LANGUE
# ═══════════════════════════════════════════════════════════════════════════════

_CRITERES = [
    ("contributors", get_nbr_contributors),
    ("size", get_size),
    ("int_links", get_nbr_int_links),
    ("ext_links", get_nbr_ext_links),
    ("visite", get_nbr_visite),
]


def collecter_criteres(wiki_domain, prolexemes, pause=0.3, progress_cb=None):
    """
    Appelle les 5 APIs Wikipedia pour chaque prolexème.

    Paramètres
    ----------
    wiki_domain : str  — ex. "pl" ou "sr"
    prolexemes : list[(num, label, wiki_link)]
    pause : float — délai entre les prolexèmes (respect rate-limit)
    progress_cb : callable(i, total, label) — callback de progression

    Retourne
    --------
    dict[num_prolexeme] → dict{contributors, size, int_links, ext_links, visite}
    """
    resultats = {}
    total = len(prolexemes)

    for i, (num, label, wiki_link) in enumerate(prolexemes):
        if progress_cb:
            progress_cb(i, total, label)

        vals = {}
        for crit_name, fn in _CRITERES:
            vals[crit_name] = fn(wiki_domain, wiki_link)

        resultats[num] = vals

        if pause and i < total - 1:
            time.sleep(pause)

    return resultats


# ═══════════════════════════════════════════════════════════════════════════════
# 3. MÉTHODE SAW — NORMALISATION + ENTROPIE + PONDÉRATION
# ═══════════════════════════════════════════════════════════════════════════════

def _normaliser(valeurs):
    """Normalise par somme (chaque valeur / somme colonne). Retourne array."""
    arr = np.array(valeurs, dtype=float)
    s = arr.sum()
    if s == 0:
        return arr
    return arr / s


def _entropie(col_normalisee):
    """Entropie de Shannon : e = (-1/ln(m)) * Σ(x·ln(x))."""
    m = len(col_normalisee)
    if m <= 1:
        return 0.0
    # Remplacer 0 par une très petite valeur pour éviter log(0)
    col = np.where(col_normalisee > 0, col_normalisee, 1e-12)
    return (-1.0 / np.log(m)) * np.sum(col * np.log(col))


def calculer_saw(resultats):
    """
    Applique la méthode SAW sur les résultats collectés.

    Paramètres
    ----------
    resultats : dict[num] → {contributors, size, int_links, ext_links, visite}

    Retourne
    --------
    dict[num] → score (float)
    """
    if not resultats:
        return {}

    nums = list(resultats.keys())
    crit_names = ["contributors", "size", "int_links", "ext_links", "visite"]

    # Construire la matrice (n prolexèmes × 5 critères)
    matrix = np.array(
        [[resultats[num][c] for c in crit_names] for num in nums],
        dtype=float,
    )

    # Normaliser chaque colonne par sa somme
    col_sums = matrix.sum(axis=0)
    col_sums[col_sums == 0] = 1  # éviter division par 0
    norm = matrix / col_sums

    # Calculer l'entropie de chaque critère
    e = np.array([_entropie(norm[:, j]) for j in range(5)])

    # Pondérations : w_i = (1 - e_i) / (5 - Σe)
    denom = 5 - e.sum()
    if denom == 0:
        weights = np.ones(5) / 5
    else:
        weights = (1 - e) / denom

    # Score SAW : somme pondérée
    scores = (norm * weights).sum(axis=1)

    return {num: float(scores[i]) for i, num in enumerate(nums)}


# ═══════════════════════════════════════════════════════════════════════════════
# 4. CLASSIFICATION EN 3 NIVEAUX
# ═══════════════════════════════════════════════════════════════════════════════

def classifier(scores):
    """
    Classe les scores en 3 niveaux de fréquence :
      1 = Fréquent     (score > μ + σ)
      2 = Peu fréquent (score > μ' + 0.5·σ')
      3 = Rare          (reste)

    Retourne dict[num] → NUM_FREQUENCY (1, 2 ou 3)
    """
    if not scores:
        return {}

    vals = np.array(list(scores.values()))
    nums = list(scores.keys())

    mean = vals.mean()
    std = vals.std()
    threshold1 = mean + std

    classes = {}
    reste_nums = []
    reste_vals = []

    for i, num in enumerate(nums):
        if vals[i] > threshold1:
            classes[num] = 1  # Fréquent
        else:
            reste_nums.append(num)
            reste_vals.append(vals[i])

    if reste_vals:
        reste_arr = np.array(reste_vals)
        mean2 = reste_arr.mean()
        std2 = reste_arr.std()
        threshold2 = mean2 + 0.5 * std2

        for j, num in enumerate(reste_nums):
            if reste_arr[j] > threshold2:
                classes[num] = 2  # Peu fréquent
            else:
                classes[num] = 3  # Rare

    return classes


# ═══════════════════════════════════════════════════════════════════════════════
# 5. FONCTION PRINCIPALE — CALCULER ET ENREGISTRER
# ═══════════════════════════════════════════════════════════════════════════════

def _get_prolexemes(lang_code):
    """Récupère les prolexèmes avec lien Wikipedia depuis la BDD."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        f"SELECT NUM_PROLEXEME, LABEL_PROLEXEME, WIKIPEDIA_LINK "
        f"FROM prolexeme_{lang_code} "
        f"WHERE WIKIPEDIA_LINK IS NOT NULL"
    ).fetchall()
    conn.close()
    return rows


def _enregistrer_frequences(lang_code, classes, year_num=24):
    """
    Enregistre les résultats dans frequency_{lang}.

    year_num : NUM_YEAR_FREQUENCY (24 = année 2024)
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    data = [(num, year_num, freq) for num, freq in classes.items()]
    cur.executemany(
        f"INSERT OR REPLACE INTO frequency_{lang_code} "
        f"(NUM_PROLEXEME, NUM_YEAR_FREQUENCY, NUM_FREQUENCY) VALUES (?, ?, ?)",
        data,
    )
    conn.commit()
    conn.close()
    return len(data)


def calculer_notoriete(lang_code, wiki_domain, pause=0.3,
                       progress_cb=None, batch_size=None):
    """
    Pipeline complet : collecte API → SAW → classification → enregistrement.

    Paramètres
    ----------
    lang_code : str — "pol" ou "srp"
    wiki_domain : str — "pl" ou "sr"
    pause : float — délai entre requêtes (respect rate-limit)
    progress_cb : callable(i, total, label) — pour affichage Streamlit
    batch_size : int|None — si défini, traite seulement les N premiers

    Retourne
    --------
    dict avec les statistiques : {total, traites, freq_1, freq_2, freq_3}
    """
    prolexemes = _get_prolexemes(lang_code)
    if batch_size:
        prolexemes = prolexemes[:batch_size]

    log.info("Collecte des critères Wikipedia pour %s (%d prolexèmes)...",
             lang_code, len(prolexemes))

    resultats = collecter_criteres(wiki_domain, prolexemes, pause, progress_cb)
    scores = calculer_saw(resultats)
    classes = classifier(scores)
    nb = _enregistrer_frequences(lang_code, classes)

    stats = {
        "total": len(prolexemes),
        "traites": nb,
        "freq_1": sum(1 for v in classes.values() if v == 1),
        "freq_2": sum(1 for v in classes.values() if v == 2),
        "freq_3": sum(1 for v in classes.values() if v == 3),
    }
    log.info("Résultats %s : %s", lang_code, stats)
    return stats


# ═══════════════════════════════════════════════════════════════════════════════
# 5b. CALCUL À LA DEMANDE — UN SEUL PROLEXÈME, TOUTES ANNÉES
# ═══════════════════════════════════════════════════════════════════════════════

_WIKI_MAP = {"srp": "sr", "pol": "pl", "arb": "ar"}
_YEARS = [19, 20, 21, 22, 23]
_VISIT_RANGES = {
    19: ("20190101", "20191231"),
    20: ("20200101", "20201231"),
    21: ("20210101", "20211231"),
    22: ("20220101", "20221231"),
    23: ("20230101", "20231231"),
}


def _get_nbr_visite_year(wiki_domain, name, start, end):
    """Visites pondérées par récence pour une période donnée."""
    from urllib.parse import quote
    enc = quote(name)
    url = (
        f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
        f"/{wiki_domain}.wikipedia/all-access/all-agents/{enc}"
        f"/monthly/{start}/{end}"
    )
    try:
        r = requests.get(url, headers={"User-Agent": _UA}, timeout=15)
        if r.status_code != 200:
            return 0
        items = r.json()["items"]
        visits = 0.0
        n = len(items)
        for idx, item in enumerate(items, 1):
            visits += item["views"] * (idx / n)
        return visits
    except Exception:
        return 0


def calculer_un_prolexeme(lang_code, num_prolexeme, wiki_link, progress_cb=None):
    """
    Calcule l'indice de notoriété pour UN SEUL prolexème, années 19-23.

    Collecte les 5 critères Wikipedia (4 fixes + visites/année),
    puis classe en comparant à la distribution existante dans la base.

    Retourne dict : {year: {"class": int, "criteres": dict}}.
    """
    wiki = _WIKI_MAP.get(lang_code)
    if not wiki:
        return {}

    if progress_cb:
        progress_cb("Collecte des critères Wikipedia…", 0.1)

    # Critères fixes (4 appels API)
    fixed = {
        "contributors": get_nbr_contributors(wiki, wiki_link),
        "size": get_size(wiki, wiki_link),
        "int_links": get_nbr_int_links(wiki, wiki_link),
        "ext_links": get_nbr_ext_links(wiki, wiki_link),
    }

    if progress_cb:
        progress_cb("Critères fixes collectés", 0.3)

    results_by_year = {}
    rows_to_insert = []  # Accumuler pour un seul push MySQL à la fin

    for yi, year in enumerate(_YEARS):
        start, end = _VISIT_RANGES[year]

        if progress_cb:
            progress_cb(f"Année 20{year} — collecte visites…", 0.35 + yi * 0.12)

        visits = _get_nbr_visite_year(wiki, wiki_link, start, end)

        # Classification par score composite calibré
        freq_class = _classifier_composite(fixed, visits)

        results_by_year[year] = {
            "class": freq_class,
            "criteres": {
                "contributeurs": fixed["contributors"],
                "taille": fixed["size"],
                "liens_internes": fixed["int_links"],
                "liens_externes": fixed["ext_links"],
                "visites": round(visits, 1),
            },
        }

        rows_to_insert.append((num_prolexeme, year, freq_class))

    # Enregistrer les 5 années en une seule transaction SQLite
    conn = sqlite3.connect(DB_PATH)
    conn.executemany(
        f"INSERT OR REPLACE INTO frequency_{lang_code} "
        f"(NUM_PROLEXEME, NUM_YEAR_FREQUENCY, NUM_FREQUENCY) VALUES (?, ?, ?)",
        rows_to_insert,
    )
    conn.commit()
    conn.close()

    if progress_cb:
        progress_cb("Terminé !", 1.0)

    return results_by_year


def _classifier_composite(fixed, visits):
    """
    Classification par score composite pondéré.

    Utilise les 5 critères normalisés par des échelles empiriques.
    Les critères qui retournent 0 (API indisponible) sont ignorés —
    seuls les critères avec une valeur > 0 contribuent au score.
    """
    # Paires (valeur brute, valeur normalisée)
    raw_norm = [
        (fixed["contributors"], min(fixed["contributors"] / 100,  1.0)),
        (fixed["size"],         min(fixed["size"]         / 50000, 1.0)),
        (fixed["int_links"],    min(fixed["int_links"]    / 500,   1.0)),
        (fixed["ext_links"],    min(fixed["ext_links"]    / 100,   1.0)),
        (visits,                min(visits               / 50000, 1.0)),
    ]

    # Ignorer les critères à 0 (API échouée ou indisponible)
    actifs = [norm for raw, norm in raw_norm if raw > 0]

    if not actifs:
        return 3   # Aucune donnée → Rare

    score = sum(actifs) / len(actifs)

    if score >= 0.35:
        return 1   # Fréquent
    elif score >= 0.12:
        return 2   # Peu fréquent
    else:
        return 3   # Rare


# ═══════════════════════════════════════════════════════════════════════════════
# 6. SYNCHRONISATION MYSQL (phpMyAdmin)
# ═══════════════════════════════════════════════════════════════════════════════

_MYSQL_CONFIG_TABLE = "CREATE TABLE IF NOT EXISTS _mysql_config (key TEXT PRIMARY KEY, value TEXT)"


def get_mysql_config():
    """Lit la config MySQL stockée dans SQLite. Retourne dict ou None."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(_MYSQL_CONFIG_TABLE)
    rows = conn.execute("SELECT key, value FROM _mysql_config").fetchall()
    conn.close()
    if not rows:
        return None
    cfg = {r[0]: r[1] for r in rows}
    required = {"host", "port", "user", "password", "database"}
    return cfg if required.issubset(cfg) else None


def set_mysql_config(host, port, user, password, database):
    """Sauvegarde la config MySQL dans SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(_MYSQL_CONFIG_TABLE)
    for k, v in [("host", host), ("port", str(port)), ("user", user),
                 ("password", password), ("database", database)]:
        conn.execute("INSERT OR REPLACE INTO _mysql_config (key, value) VALUES (?, ?)", (k, v))
    conn.commit()
    conn.close()


def test_mysql_connection():
    """Teste la connexion MySQL. Retourne (True, message) ou (False, erreur)."""
    cfg = get_mysql_config()
    if not cfg:
        return False, "No MySQL configuration is registered."
    try:
        import pymysql
        cnx = pymysql.connect(
            host=cfg["host"], port=int(cfg["port"]),
            user=cfg["user"], password=cfg["password"],
            database=cfg["database"], connect_timeout=5,
        )
        cnx.close()
        return True, f"Connexion réussie à {cfg['host']}:{cfg['port']}/{cfg['database']}"
    except Exception as e:
        return False, str(e)


def _push_frequency_mysql(lang_code, num_prolexeme, year, num_frequency):
    """Pousse UNE ligne de fréquence vers MySQL (silencieux si non configuré)."""
    _push_frequency_mysql_batch(lang_code, [(num_prolexeme, year, num_frequency)])


def _push_frequency_mysql_batch(lang_code, rows):
    """Pousse plusieurs lignes (num_prolexeme, year, freq) en une seule connexion MySQL."""
    cfg = get_mysql_config()
    if not cfg:
        return
    try:
        import pymysql
        cnx = pymysql.connect(
            host=cfg["host"], port=int(cfg["port"]),
            user=cfg["user"], password=cfg["password"],
            database=cfg["database"], connect_timeout=5,
        )
        cur = cnx.cursor()
        cur.executemany(
            f"INSERT INTO `frequency_{lang_code}` "
            f"(`NUM_PROLEXEME`, `NUM_YEAR_FREQUENCY`, `NUM_FREQUENCY`) "
            f"VALUES (%s, %s, %s) "
            f"ON DUPLICATE KEY UPDATE `NUM_FREQUENCY` = VALUES(`NUM_FREQUENCY`)",
            rows,
        )
        cnx.commit()
        cnx.close()
    except Exception as e:
        log.warning("MySQL batch push failed (%s): %s", lang_code, e)


def push_prolexeme_to_mysql(lang_code, num_prolexeme, max_retries=3):
    """Pousse les fréquences d'UN prolexème vers MySQL avec retries. Retourne (ok, message)."""
    cfg = get_mysql_config()
    if not cfg:
        return False, "No MySQL configuration is available."
    rows = sqlite3.connect(DB_PATH).execute(
        f"SELECT NUM_PROLEXEME, NUM_YEAR_FREQUENCY, NUM_FREQUENCY "
        f"FROM frequency_{lang_code} WHERE NUM_PROLEXEME = ?",
        (num_prolexeme,),
    ).fetchall()
    if not rows:
        return False, f"No local data are available for {lang_code}/{num_prolexeme}."
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            import pymysql
            cnx = pymysql.connect(
                host=cfg["host"], port=int(cfg["port"]),
                user=cfg["user"], password=cfg["password"],
                database=cfg["database"], connect_timeout=10,
                read_timeout=10, write_timeout=10,
            )
            cur = cnx.cursor()
            cur.executemany(
                f"INSERT INTO `frequency_{lang_code}` "
                f"(`NUM_PROLEXEME`, `NUM_YEAR_FREQUENCY`, `NUM_FREQUENCY`) "
                f"VALUES (%s, %s, %s) "
                f"ON DUPLICATE KEY UPDATE `NUM_FREQUENCY` = VALUES(`NUM_FREQUENCY`)",
                rows,
            )
            cnx.commit()
            cnx.close()
            return True, f"{len(rows)} lignes enregistrées ({lang_code}, tentative {attempt})."
        except Exception as e:
            last_err = str(e)
            log.warning("MySQL push attempt %d failed (%s/%s): %s", attempt, lang_code, num_prolexeme, e)
    return False, f"Échec après {max_retries} tentatives : {last_err}"


def is_prolexeme_in_mysql(lang_code, num_prolexeme):
    """Vérifie si un prolexème est déjà présent dans MySQL. Retourne True/False."""
    cfg = get_mysql_config()
    if not cfg:
        return False
    try:
        import pymysql
        cnx = pymysql.connect(
            host=cfg["host"], port=int(cfg["port"]),
            user=cfg["user"], password=cfg["password"],
            database=cfg["database"], connect_timeout=5,
        )
        cur = cnx.cursor()
        cur.execute(
            f"SELECT COUNT(*) FROM `frequency_{lang_code}` WHERE `NUM_PROLEXEME` = %s",
            (num_prolexeme,),
        )
        count = cur.fetchone()[0]
        cnx.close()
        return count > 0
    except Exception:
        return False


def check_prolexemes_in_mysql(pairs):
    """Vérifie plusieurs (lang_code, num_prolexeme) en UNE SEULE connexion MySQL.
    pairs : list de (lang_code, num_prolexeme)
    Retourne un set de (lang_code, num_prolexeme) présents dans MySQL.
    """
    if not pairs:
        return set()
    cfg = get_mysql_config()
    if not cfg:
        return set()
    result = set()
    try:
        import pymysql
        cnx = pymysql.connect(
            host=cfg["host"], port=int(cfg["port"]),
            user=cfg["user"], password=cfg["password"],
            database=cfg["database"], connect_timeout=2,
        )
        cur = cnx.cursor()
        for lang_code, num in pairs:
            cur.execute(
                f"SELECT COUNT(*) FROM `frequency_{lang_code}` WHERE `NUM_PROLEXEME` = %s",
                (num,),
            )
            if cur.fetchone()[0] > 0:
                result.add((lang_code, num))
        cnx.close()
    except Exception:
        pass
    return result


def push_all_to_mysql():
    """Pousse toutes les lignes frequency_* de SQLite vers MySQL. Retourne (n_ok, erreur)."""
    cfg = get_mysql_config()
    if not cfg:
        return 0, "No MySQL configuration is available."
    try:
        import pymysql
        cnx = pymysql.connect(
            host=cfg["host"], port=int(cfg["port"]),
            user=cfg["user"], password=cfg["password"],
            database=cfg["database"], connect_timeout=10,
        )
        cur = cnx.cursor()
        sqlite_conn = sqlite3.connect(DB_PATH)
        total = 0
        for lc in ["arb", "pol", "srp"]:
            rows = sqlite_conn.execute(
                f"SELECT NUM_PROLEXEME, NUM_YEAR_FREQUENCY, NUM_FREQUENCY FROM frequency_{lc}"
            ).fetchall()
            for row in rows:
                cur.execute(
                    f"INSERT INTO `frequency_{lc}` "
                    f"(`NUM_PROLEXEME`,`NUM_YEAR_FREQUENCY`,`NUM_FREQUENCY`) "
                    f"VALUES (%s,%s,%s) "
                    f"ON DUPLICATE KEY UPDATE `NUM_FREQUENCY`=VALUES(`NUM_FREQUENCY`)",
                    row,
                )
                total += 1
        cnx.commit()
        sqlite_conn.close()
        cnx.close()
        return total, None
    except Exception as e:
        return 0, str(e)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. FONCTIONS DE LECTURE (pour l'affichage dans l'app)
# ═══════════════════════════════════════════════════════════════════════════════

def get_frequences_prolexeme(lang_code, num_prolexeme):
    """
    Retourne l'historique de fréquence d'un prolexème.
    Liste de (année, label_fréquence).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        f"SELECT yf.YEAR_FREQUENCY, f.FRA_FREQUENCY, fl.NUM_FREQUENCY "
        f"FROM frequency_{lang_code} fl "
        f"JOIN year_frequency yf ON fl.NUM_YEAR_FREQUENCY = yf.NUM_YEAR_FREQUENCY "
        f"JOIN frequency f ON fl.NUM_FREQUENCY = f.NUM_FREQUENCY "
        f"WHERE fl.NUM_PROLEXEME = ? "
        f"ORDER BY yf.YEAR_FREQUENCY",
        (num_prolexeme,),
    ).fetchall()
    conn.close()
    return rows


def get_stats_frequence(lang_code):
    """Statistiques globales de fréquence pour une langue."""
    conn = sqlite3.connect(DB_PATH)
    total = conn.execute(
        f"SELECT COUNT(DISTINCT NUM_PROLEXEME) FROM frequency_{lang_code}"
    ).fetchone()[0]
    dist = conn.execute(
        f"SELECT f.FRA_FREQUENCY, COUNT(DISTINCT fl.NUM_PROLEXEME) "
        f"FROM frequency_{lang_code} fl "
        f"JOIN frequency f ON fl.NUM_FREQUENCY = f.NUM_FREQUENCY "
        f"GROUP BY f.FRA_FREQUENCY ORDER BY fl.NUM_FREQUENCY"
    ).fetchall()
    conn.close()
    return {"total": total, "distribution": dist}


def get_prolexeme_avec_frequence(lang_code, num_frequency=None, limit=50):
    """Liste des prolexèmes avec leur fréquence la plus récente."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    where = ""
    params = []
    if num_frequency:
        where = "AND fl.NUM_FREQUENCY = ?"
        params.append(num_frequency)
    rows = conn.execute(
        f"SELECT p.NUM_PROLEXEME, p.LABEL_PROLEXEME, p.WIKIPEDIA_LINK, "
        f"f.FRA_FREQUENCY, fl.NUM_FREQUENCY, yf.YEAR_FREQUENCY "
        f"FROM prolexeme_{lang_code} p "
        f"JOIN frequency_{lang_code} fl ON p.NUM_PROLEXEME = fl.NUM_PROLEXEME "
        f"JOIN frequency f ON fl.NUM_FREQUENCY = f.NUM_FREQUENCY "
        f"JOIN year_frequency yf ON fl.NUM_YEAR_FREQUENCY = yf.NUM_YEAR_FREQUENCY "
        f"WHERE 1=1 {where} "
        f"ORDER BY fl.NUM_FREQUENCY, p.LABEL_PROLEXEME "
        f"LIMIT ?",
        params + [limit],
    ).fetchall()
    conn.close()
    return rows


# ═══════════════════════════════════════════════════════════════════════════════
# CLI — Exécution directe pour peupler la base
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    lang = sys.argv[1] if len(sys.argv) > 1 else "srp"
    wiki = {"pol": "pl", "srp": "sr"}.get(lang, lang[:2])
    batch = int(sys.argv[2]) if len(sys.argv) > 2 else None

    def _progress(i, total, label):
        pct = (i + 1) * 100 // total
        print(f"\r  [{pct:3d}%] {i+1}/{total} — {label}", end="", flush=True)

    print(f"Calcul de notoriété pour {lang} (Wikipedia {wiki})...")
    stats = calculer_notoriete(lang, wiki, pause=0.3,
                               progress_cb=_progress, batch_size=batch)
    print(f"\n\nRésultats : {stats}")
