# -*- coding: utf-8 -*-
"""
Module d'accès à la base ProLexBase (SQLite).
Fournit des fonctions de lecture pour les prolexèmes arabes,
leurs instances, dérivés, pivots et types.
"""
import sqlite3
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.environ.get(
    "PROLEXARABIC_DB",
    os.path.join(PROJECT_ROOT, "data_sample", "prolexbase_sample.db"),
)


def _conn():
    """Retourne une connexion SQLite en mode lecture seule."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


# ─── Types ───────────────────────────────────────────────────────────────────

def get_all_types():
    """Retourne tous les types (id, nom_fr, nom_eng, note, supertype)."""
    with _conn() as c:
        return c.execute(
            "SELECT NUM_TYPE, FRA_TYPE, ENG_TYPE, NOTE, NUM_TYPE_SUPERTYPE "
            "FROM type ORDER BY NUM_TYPE"
        ).fetchall()


def get_type_by_id(num_type):
    with _conn() as c:
        return c.execute(
            "SELECT NUM_TYPE, FRA_TYPE, ENG_TYPE, NOTE FROM type WHERE NUM_TYPE=?",
            (num_type,)
        ).fetchone()


# ─── Statistiques ────────────────────────────────────────────────────────────

def get_stats():
    """Statistiques globales de la base."""
    with _conn() as c:
        nb_prolexemes = c.execute("SELECT COUNT(*) FROM prolexeme_arb").fetchone()[0]
        nb_instances = c.execute("SELECT COUNT(*) FROM instance_arb").fetchone()[0]
        nb_derivatives = c.execute("SELECT COUNT(*) FROM derivative_arb").fetchone()[0]
        nb_pivots = c.execute("SELECT COUNT(*) FROM pivot").fetchone()[0]
        nb_types = c.execute("SELECT COUNT(*) FROM type").fetchone()[0]
    return {
        "prolexemes": nb_prolexemes,
        "instances": nb_instances,
        "derivatives": nb_derivatives,
        "pivots": nb_pivots,
        "types": nb_types,
    }


def get_type_distribution():
    """Nombre de prolexèmes par type."""
    with _conn() as c:
        return c.execute(
            "SELECT t.FRA_TYPE, COUNT(*) as nb "
            "FROM prolexeme_arb p "
            "JOIN pivot pv ON p.NUM_PIVOT=pv.NUM_PIVOT "
            "JOIN type t ON pv.NUM_TYPE=t.NUM_TYPE "
            "GROUP BY t.FRA_TYPE ORDER BY nb DESC"
        ).fetchall()


# ─── Prolexèmes ─────────────────────────────────────────────────────────────

def search_prolexemes(query="", type_filter=None, page=1, per_page=50):
    """
    Recherche paginée dans les prolexèmes arabes.
    Retourne (rows, total_count).
    """
    conditions = []
    params = []

    if query:
        conditions.append("p.LABEL_PROLEXEME LIKE ?")
        params.append(f"%{query}%")
    if type_filter:
        conditions.append("t.FRA_TYPE = ?")
        params.append(type_filter)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    base_sql = (
        "FROM prolexeme_arb p "
        "JOIN pivot pv ON p.NUM_PIVOT = pv.NUM_PIVOT "
        "JOIN type t ON pv.NUM_TYPE = t.NUM_TYPE "
        f"{where}"
    )

    with _conn() as c:
        total = c.execute(f"SELECT COUNT(*) {base_sql}", params).fetchone()[0]
        offset = (page - 1) * per_page
        rows = c.execute(
            f"SELECT p.NUM_PROLEXEME, p.LABEL_PROLEXEME, p.NUM_PIVOT, "
            f"t.FRA_TYPE, t.NUM_TYPE, p.WIKIPEDIA_LINK "
            f"{base_sql} "
            f"ORDER BY p.LABEL_PROLEXEME "
            f"LIMIT ? OFFSET ?",
            params + [per_page, offset]
        ).fetchall()

    return rows, total


def get_prolexeme_by_id(num_prolexeme):
    """Détail d'un prolexème avec son type."""
    with _conn() as c:
        return c.execute(
            "SELECT p.NUM_PROLEXEME, p.LABEL_PROLEXEME, p.NUM_PIVOT, "
            "p.WIKIPEDIA_LINK, t.FRA_TYPE, t.ENG_TYPE, t.NUM_TYPE "
            "FROM prolexeme_arb p "
            "JOIN pivot pv ON p.NUM_PIVOT = pv.NUM_PIVOT "
            "JOIN type t ON pv.NUM_TYPE = t.NUM_TYPE "
            "WHERE p.NUM_PROLEXEME = ?",
            (num_prolexeme,)
        ).fetchone()


def get_prolexeme_by_pivot(num_pivot):
    """Tous les prolexèmes liés à un pivot."""
    with _conn() as c:
        return c.execute(
            "SELECT p.NUM_PROLEXEME, p.LABEL_PROLEXEME, p.NUM_PIVOT, "
            "p.WIKIPEDIA_LINK, t.FRA_TYPE, t.NUM_TYPE "
            "FROM prolexeme_arb p "
            "JOIN pivot pv ON p.NUM_PIVOT = pv.NUM_PIVOT "
            "JOIN type t ON pv.NUM_TYPE = t.NUM_TYPE "
            "WHERE p.NUM_PIVOT = ?",
            (num_pivot,)
        ).fetchall()


# ─── Dérivés ─────────────────────────────────────────────────────────────────

def get_derivatives_by_prolexeme(num_prolexeme):
    """Dérivés d'un prolexème (via son pivot)."""
    with _conn() as c:
        return c.execute(
            "SELECT d.NUM_DERIVATIVE, d.LABEL_DERIVATIVE, "
            "dc.FRA_CATEGORY, dc.ENG_CATEGORY "
            "FROM derivative_arb d "
            "JOIN derivative_category dc ON d.NUM_DERIVATIVE_CATEGORY = dc.NUM_DERIVATIVE_CATEGORY "
            "JOIN prolexeme_arb p ON p.NUM_PIVOT = d.NUM_PIVOT "
            "WHERE p.NUM_PROLEXEME = ?",
            (num_prolexeme,)
        ).fetchall()


# ─── Instances ───────────────────────────────────────────────────────────────

def get_instances_by_prolexeme(num_prolexeme):
    """Instances (flexions) d'un prolexème."""
    with _conn() as c:
        return c.execute(
            "SELECT i.NUM_INSTANCE, i.LABEL_INSTANCE, "
            "m.GENDER, m.NUMBER, m.[CASE], m.DEFINITENESS, "
            "i.NUM_DERIVATIVE "
            "FROM instance_arb i "
            "LEFT JOIN morphology_arb m ON i.NUM_MORPHOLOGY = m.NUM_MORPHOLOGY "
            "WHERE i.NUM_PROLEXEME = ? "
            "ORDER BY m.GENDER, m.NUMBER, m.[CASE], m.DEFINITENESS",
            (num_prolexeme,)
        ).fetchall()


# ─── Pivot ───────────────────────────────────────────────────────────────────

def get_pivot_info(num_pivot):
    """Informations sur un pivot."""
    with _conn() as c:
        return c.execute(
            "SELECT pv.NUM_PIVOT, pv.NUM_TYPE, t.FRA_TYPE, t.ENG_TYPE, t.NOTE "
            "FROM pivot pv "
            "JOIN type t ON pv.NUM_TYPE = t.NUM_TYPE "
            "WHERE pv.NUM_PIVOT = ?",
            (num_pivot,)
        ).fetchone()


# ─── Relations sémantiques (MySQL) ───────────────────────────────────────────

def _get_mysql_cfg():
    """Lit la configuration MySQL depuis SQLite (_mysql_config)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT key, value FROM _mysql_config").fetchall()
        conn.close()
        cfg = {r[0]: r[1] for r in rows}
        required = {"host", "port", "user", "password", "database"}
        return cfg if required.issubset(cfg) else None
    except Exception:
        return None


def _mysql_conn():
    """Retourne une connexion pymysql depuis la config stockée, ou None."""
    cfg = _get_mysql_cfg()
    if not cfg:
        return None
    try:
        import pymysql
        return pymysql.connect(
            host=cfg["host"], port=int(cfg["port"]),
            user=cfg["user"], password=cfg["password"],
            database=cfg["database"], connect_timeout=5,
            cursorclass=pymysql.cursors.DictCursor,
        )
    except Exception:
        return None


def _pivot_labels(pivot_ids):
    """Retourne {num_pivot: label} pour une liste d'IDs pivot (SQLite)."""
    if not pivot_ids:
        return {}
    placeholders = ",".join("?" * len(pivot_ids))
    with _conn() as c:
        rows = c.execute(
            f"SELECT NUM_PIVOT, LABEL_PROLEXEME FROM prolexeme_arb "
            f"WHERE NUM_PIVOT IN ({placeholders})",
            pivot_ids,
        ).fetchall()
    return {r[0]: r[1] for r in rows}


def get_synonymes(num_pivot):
    """Synonymes d'un pivot (requête MySQL + labels SQLite).
    Retourne liste de dicts {num_pivot, label}.
    """
    cnx = _mysql_conn()
    if not cnx:
        return []
    try:
        with cnx.cursor() as cur:
            cur.execute(
                "SELECT `NUM_PIVOT-SYNONYMOUS` AS pid FROM synonymy "
                "WHERE `NUM_PIVOT-CANONICAL` = %s "
                "UNION "
                "SELECT `NUM_PIVOT-CANONICAL` AS pid FROM synonymy "
                "WHERE `NUM_PIVOT-SYNONYMOUS` = %s",
                (num_pivot, num_pivot),
            )
            pivot_ids = [r["pid"] for r in cur.fetchall()]
    finally:
        cnx.close()
    labels = _pivot_labels(pivot_ids)
    return [{"num_pivot": pid, "label": labels.get(pid, f"pivot#{pid}")} for pid in pivot_ids]


def get_meronymie(num_pivot):
    """Méronymie d'un pivot (requête MySQL + labels SQLite).
    Retourne dict avec clés 'parties' (méronymie) et 'tout' (holonymie).
    """
    cnx = _mysql_conn()
    if not cnx:
        return {"parties": [], "tout": []}
    try:
        with cnx.cursor() as cur:
            # Ce pivot est le tout (holonymous) → les parties (meronymous)
            cur.execute(
                "SELECT `NUM_PIVOT-MERONYMOUS` AS pid FROM meronymy "
                "WHERE `NUM_PIVOT-HOLONYMOUS` = %s",
                (num_pivot,),
            )
            parties_ids = [r["pid"] for r in cur.fetchall()]
            # Ce pivot est une partie (meronymous) → les touts (holonymous)
            cur.execute(
                "SELECT `NUM_PIVOT-HOLONYMOUS` AS pid FROM meronymy "
                "WHERE `NUM_PIVOT-MERONYMOUS` = %s",
                (num_pivot,),
            )
            tout_ids = [r["pid"] for r in cur.fetchall()]
    finally:
        cnx.close()
    all_ids = list(set(parties_ids + tout_ids))
    labels = _pivot_labels(all_ids)
    parties = [{"num_pivot": pid, "label": labels.get(pid, f"pivot#{pid}")} for pid in parties_ids]
    tout = [{"num_pivot": pid, "label": labels.get(pid, f"pivot#{pid}")} for pid in tout_ids]
    return {"parties": parties, "tout": tout}


def get_accessibilite(num_pivot):
    """Accessibilité d'un pivot (requête MySQL + labels SQLite).
    Retourne dict avec 'accessible_depuis' et 'donne_acces_a'.
    """
    cnx = _mysql_conn()
    if not cnx:
        return {"accessible_depuis": [], "donne_acces_a": []}
    try:
        with cnx.cursor() as cur:
            # Ce pivot est ARG2 (destination) → ARG1 (source) donne accès à ce pivot
            cur.execute(
                "SELECT `NUM_PIVOT-ARGUMENT1` AS pid FROM accessibility "
                "WHERE `NUM_PIVOT-ARGUMENT2` = %s",
                (num_pivot,),
            )
            depuis_ids = [r["pid"] for r in cur.fetchall()]
            # Ce pivot est ARG1 (source) → ARG2 (destination) accessible
            cur.execute(
                "SELECT `NUM_PIVOT-ARGUMENT2` AS pid FROM accessibility "
                "WHERE `NUM_PIVOT-ARGUMENT1` = %s",
                (num_pivot,),
            )
            vers_ids = [r["pid"] for r in cur.fetchall()]
    finally:
        cnx.close()
    all_ids = list(set(depuis_ids + vers_ids))
    labels = _pivot_labels(all_ids)
    accessible_depuis = [{"num_pivot": pid, "label": labels.get(pid, f"pivot#{pid}")} for pid in depuis_ids]
    donne_acces_a = [{"num_pivot": pid, "label": labels.get(pid, f"pivot#{pid}")} for pid in vers_ids]
    return {"accessible_depuis": accessible_depuis, "donne_acces_a": donne_acces_a}
