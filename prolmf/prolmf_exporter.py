import mysql.connector
import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path
import os
import yaml


def safe_str(val):
    return "" if val is None else str(val)




def normalize_frequency_label(label):
    """
    Harmonise les libellés de fréquence avec le XSD / les consignes du projet.
    """
    if label is None:
        return ""
    value = str(label).strip()
    if value == "infrequentlyUsed":
        return "unfrequentlyUsed"
    return value


def xml_escape(text):
    if text is None:
        return ""
    return str(text)


def prettify_xml(elem):
    rough_string = ET.tostring(elem, encoding="utf-8")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="    ")


def add_unique_subcategorization_frame(lexicon_elem, created_ids, frame_id, text=None, attrs=None):
    if not frame_id or frame_id in created_ids:
        return
    attrs = attrs or {}
    attrs = {"id": frame_id, **attrs}
    frame = ET.SubElement(lexicon_elem, "SubcategorizationFrame", attrs)
    if text:
        frame.text = xml_escape(text)
    created_ids.add(frame_id)


# -------------------------------------------------
# CONFIGURATION
# -------------------------------------------------
CONFIG_PATH = Path(os.getenv("PROLEX_CONFIG", "config.yaml"))
if not CONFIG_PATH.exists():
    raise FileNotFoundError(
        f"Configuration file not found: {CONFIG_PATH}. "
        "Copy config.example.yaml to config.yaml, edit the database settings, "
        "or set PROLEX_CONFIG to another YAML file."
    )
with CONFIG_PATH.open("r", encoding="utf-8") as _fh:
    _cfg = yaml.safe_load(_fh) or {}
_db = _cfg.get("database", {})

DB_HOST = _db.get("host", "localhost")
DB_USER = _db.get("user", "")
DB_PASSWORD = _db.get("password", "")
DB_NAME = _db.get("name", "")

LANGUAGES = ["arb", "deu", "eng", "fra", "ita", "kor", "nld", "pol", "por", "spa", "srp"]

XML_OUTPUT = _cfg.get("output", {}).get("prolmf_file", "outputs/prolmf_full.xml")
XSD_NAME = "ProLMF_4.xsd"
VERSION = "4.1"


# -------------------------------------------------
# CONNEXION
# -------------------------------------------------
conn = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME
)
cursor = conn.cursor(dictionary=True)

# -------------------------------------------------
# RACINE XML
# -------------------------------------------------
lexical_resource = ET.Element("LexicalResource", {
    "xmlns": "https://www.ortolang.fr/market/lexicons/prolex/v4.1",
    "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
    "xsi:schemaLocation": f"https://www.ortolang.fr/market/lexicons/prolex/v4.1/ {XSD_NAME}"
})

ET.SubElement(lexical_resource, "GlobalInformation", {
    "languageCoding": "ISO 639",
    "scriptCoding": "ISO 15924",
    "characterCoding": "UTF-8",
    "entrySource": "Prolexbase",
    "resourceName": "ProLMF",
    "version": VERSION
})

# Pivots globaux présents dans les langues exportées
global_pivots = set()
global_meronymous_pivots = set()
global_synonymous_pivots = set()
global_argument2_pivots = set()

# SenseAxis globaux déjà créés
sense_axes = {}


# -------------------------------------------------
# OUTILS SQL
# -------------------------------------------------
def fetch_all(query, params=None):
    c = conn.cursor(dictionary=True)
    c.execute(query, params or ())
    rows = c.fetchall()
    c.close()
    return rows


def fetch_one(query, params=None):
    c = conn.cursor(dictionary=True)
    c.execute(query, params or ())
    row = c.fetchone()
    c.close()
    return row


def table_exists(table_name):
    row = fetch_one(
        """
        SELECT COUNT(*) AS cnt
        FROM information_schema.tables
        WHERE table_schema = %s AND table_name = %s
        """,
        (DB_NAME, table_name)
    )
    return row and row["cnt"] > 0


# -------------------------------------------------
# DETECTION DES COLONNES SPECIALES D'INSTANCE
# -------------------------------------------------
def get_instance_columns(lang):
    cols = fetch_all(f"SHOW COLUMNS FROM `instance_{lang}`")
    col_names = [c["Field"] for c in cols]
    return {
        "has_num_script": "NUM_SCRIPT" in col_names,
        "has_num_dialect": "NUM_DIALECT" in col_names
    }




def get_table_column_names(table_name):
    if not table_exists(table_name):
        return set()
    cols = fetch_all(f"SHOW COLUMNS FROM `{table_name}`")
    return {c["Field"] for c in cols}


def resolve_lexicon_script(lang, instance_cols=None):
    """
    Détermine le script du lexique en privilégiant la table language/script.
    Cela évite de déduire le script du lexique à partir des instances, qui
    peuvent contenir des formes translittérées ou des variantes secondaires.

    Ordre de priorité :
    1) script déclaré dans language.NUM_SCRIPT -> script.ISO_CODE
    2) correction de sécurité pour le serbe : srp -> cyrl
    3) scripts présents dans instance_<lang>, seulement comme secours
    4) latn par défaut de secours
    """
    language_row = fetch_one("""
        SELECT script.ISO_CODE
        FROM language
        LEFT JOIN script
          ON language.NUM_SCRIPT = script.NUM_SCRIPT
        WHERE language.ISO_CODE = %s
    """, (lang,))
    if language_row and language_row.get("ISO_CODE"):
        return language_row["ISO_CODE"]

    # Sécurité demandée dans les remarques : le lexique serbe doit être en cyrillique.
    if lang == "srp":
        return "cyrl"

    instance_table = f"instance_{lang}"
    if instance_cols and instance_cols.get("has_num_script") and table_exists(instance_table):
        rows = fetch_all(f"""
            SELECT s.ISO_CODE, COUNT(*) AS cnt
            FROM `{instance_table}` AS i
            JOIN script AS s
              ON i.NUM_SCRIPT = s.NUM_SCRIPT
            WHERE i.NUM_SCRIPT IS NOT NULL
            GROUP BY s.ISO_CODE
            ORDER BY cnt DESC, s.ISO_CODE ASC
        """)
        if rows and rows[0].get("ISO_CODE"):
            return rows[0]["ISO_CODE"]

    return "latn"

def build_morphology_attrs(morph_row):
    wf_attrs = {}
    if not morph_row:
        return wf_attrs

    mapping = {
        "GENDER": "grammaticalGender",
        "NUMBER": "grammaticalNumber",
        "CASE": "grammaticalCase",
        "ANIMACY": "grammaticalAnimacy",
        "DEFINITENESS": "grammaticalDefiniteness",
        "DEGREE": "grammaticalDegree",
        "TAM": "grammaticalTam",
        "PERSON": "grammaticalPerson",
    }
    for src, dest in mapping.items():
        value = morph_row.get(src)
        if value is not None:
            wf_attrs[dest] = safe_str(value)
    return wf_attrs

# -------------------------------------------------
# CREATION / RECUPERATION SENSEAXIS GLOBAL
# -------------------------------------------------
def get_or_create_sense_axis(pivot_id):
    if pivot_id in sense_axes:
        return sense_axes[pivot_id]

    pivot_row = fetch_one(f"""
        SELECT pivot.NUM_PIVOT, type.ENG_TYPE, existence.ENG_EXISTENCE
        FROM pivot, type, existence
        WHERE pivot.NUM_TYPE = type.NUM_TYPE
          AND pivot.NUM_EXISTENCE = existence.NUM_EXISTENCE
          AND pivot.NUM_PIVOT = %s
    """, (pivot_id,))

    if not pivot_row:
        sense_axis = ET.Element("SenseAxis", {"id": safe_str(pivot_id)})
        sense_axes[pivot_id] = sense_axis
        return sense_axis

    sense_axis = ET.Element("SenseAxis", {"id": safe_str(pivot_id)})
    sense_axes[pivot_id] = sense_axis

    ET.SubElement(
        sense_axis,
        "InterlingualExternalRef",
        {
            "externalSystem": "typology",
            "externalReference": safe_str(pivot_row["ENG_TYPE"])
        }
    )

    ET.SubElement(
        sense_axis,
        "InterlingualExternalRef",
        {
            "externalSystem": "existence",
            "externalReference": safe_str(pivot_row["ENG_EXISTENCE"])
        }
    )

    meronymies = fetch_all("""
        SELECT `NUM_PIVOT-MERONYMOUS`
        FROM meronymy
        WHERE `NUM_PIVOT-HOLONYMOUS` = %s
    """, (pivot_id,))
    for row in meronymies:
        if row["NUM_PIVOT-MERONYMOUS"] in global_meronymous_pivots:
            ET.SubElement(
                sense_axis,
                "SenseAxisRelation",
                {
                    "label": "partitiveRelation",
                    "refSenseAxis": safe_str(row["NUM_PIVOT-MERONYMOUS"])
                }
            )

    synonymies = fetch_all("""
        SELECT `NUM_PIVOT-SYNONYMOUS`, diasystem.ENG_DIASYSTEM
        FROM synonymy, diasystem
        WHERE synonymy.NUM_DIASYSTEM = diasystem.NUM_DIASYSTEM
          AND `NUM_PIVOT-CANONICAL` = %s
    """, (pivot_id,))
    for row in synonymies:
        if row["NUM_PIVOT-SYNONYMOUS"] in global_synonymous_pivots:
            ET.SubElement(
                sense_axis,
                "SenseAxisRelation",
                {
                    "label": "quasiSynonym",
                    "refSenseAxis": safe_str(row["NUM_PIVOT-SYNONYMOUS"]),
                    "usageNote": safe_str(row["ENG_DIASYSTEM"])
                }
            )

    accessibilities = fetch_all("""
        SELECT `NUM_PIVOT-ARGUMENT2`, `NUM_ACCESSIBILITY`, subject_file.ENG_SUBJECT_FILE
        FROM accessibility, subject_file
        WHERE accessibility.NUM_SUBJECT_FILE = subject_file.NUM_SUBJECT_FILE
          AND `NUM_PIVOT-ARGUMENT1` = %s
    """, (pivot_id,))
    for row in accessibilities:
        if row["NUM_PIVOT-ARGUMENT2"] in global_argument2_pivots:
            ET.SubElement(
                sense_axis,
                "SenseAxisRelation",
                {
                    "id": safe_str(row["NUM_ACCESSIBILITY"]),
                    "label": "associativeRelation",
                    "refSenseAxis": safe_str(row["NUM_PIVOT-ARGUMENT2"]),
                    "subjectField": safe_str(row["ENG_SUBJECT_FILE"])
                }
            )

    return sense_axis


# -------------------------------------------------
# LANGUES
# -------------------------------------------------
for lang in LANGUAGES:
    print(f"Traitement de {lang}")

    language_row = fetch_one("""
        SELECT WIKIPEDIA_LINK
        FROM language
        WHERE ISO_CODE = %s
    """, (lang,))

    instance_cols = get_instance_columns(lang)
    script_code = resolve_lexicon_script(lang, instance_cols)
    wikipedia_base = language_row["WIKIPEDIA_LINK"] if language_row and language_row["WIKIPEDIA_LINK"] else f"https://{lang[:2]}.wikipedia.org/wiki/"

    lexicon = ET.SubElement(
        lexical_resource,
        "Lexicon",
        {
            "languageIdentifier": lang,
            "script": script_code
        }
    )

    subcat_frames_created = set()

    select_cols = [
        "NUM_INSTANCE", "LABEL_INSTANCE", "NUM_MORPHOLOGY", "NUM_PART_OF_SPEECH",
        "NUM_PIVOT", "NUM_PROLEXEME", "NUM_ALIAS", "NUM_DERIVATIVE"
    ]
    if instance_cols["has_num_script"]:
        select_cols.append("NUM_SCRIPT")
    if instance_cols["has_num_dialect"]:
        select_cols.append("NUM_DIALECT")

    order_cols = [
        "NUM_PIVOT ASC", "NUM_PROLEXEME ASC", "NUM_ALIAS ASC",
        "NUM_DERIVATIVE ASC", "NUM_MORPHOLOGY ASC"
    ]
    if instance_cols["has_num_script"]:
        order_cols.append("NUM_SCRIPT DESC")
    if instance_cols["has_num_dialect"]:
        order_cols.append("NUM_DIALECT ASC")

    instances = fetch_all(f"""
        SELECT {", ".join([f"`{c}`" for c in select_cols])}
        FROM `instance_{lang}`
        ORDER BY {", ".join(order_cols)}
    """)

    pivot_rows = fetch_all(f"SELECT DISTINCT NUM_PIVOT FROM `instance_{lang}`")
    lang_pivots = {row["NUM_PIVOT"] for row in pivot_rows if row["NUM_PIVOT"] is not None}
    global_pivots.update(lang_pivots)

    alias_rows = fetch_all(f"SELECT DISTINCT NUM_ALIAS FROM `instance_{lang}`")
    lang_aliases = {row["NUM_ALIAS"] for row in alias_rows if row["NUM_ALIAS"] is not None}

    if lang_pivots:
        placeholders = ", ".join(["%s"] * len(lang_pivots))

        rows = fetch_all(f"""
            SELECT `NUM_PIVOT-MERONYMOUS`
            FROM meronymy
            WHERE `NUM_PIVOT-MERONYMOUS` IN ({placeholders})
        """, tuple(lang_pivots))
        global_meronymous_pivots.update(r["NUM_PIVOT-MERONYMOUS"] for r in rows if r["NUM_PIVOT-MERONYMOUS"] is not None)

        rows = fetch_all(f"""
            SELECT `NUM_PIVOT-SYNONYMOUS`
            FROM synonymy
            WHERE `NUM_PIVOT-SYNONYMOUS` IN ({placeholders})
        """, tuple(lang_pivots))
        global_synonymous_pivots.update(r["NUM_PIVOT-SYNONYMOUS"] for r in rows if r["NUM_PIVOT-SYNONYMOUS"] is not None)

        rows = fetch_all(f"""
            SELECT `NUM_PIVOT-ARGUMENT2`
            FROM accessibility
            WHERE `NUM_PIVOT-ARGUMENT2` IN ({placeholders})
        """, tuple(lang_pivots))
        global_argument2_pivots.update(r["NUM_PIVOT-ARGUMENT2"] for r in rows if r["NUM_PIVOT-ARGUMENT2"] is not None)

    grouped_entries = {}
    for row in instances:
        key = (row["NUM_PROLEXEME"], row["NUM_ALIAS"], row["NUM_DERIVATIVE"])
        grouped_entries.setdefault(key, []).append(row)

    sorted_keys = sorted(grouped_entries.keys(), key=lambda x: (
        x[0] if x[0] is not None else -1,
        x[1] if x[1] is not None else -1,
        x[2] if x[2] is not None else -1
    ))

    for key in sorted_keys:
        group = grouped_entries[key]
        first = group[0]

        num_pivot = first["NUM_PIVOT"]
        num_prolexeme = first["NUM_PROLEXEME"]
        num_alias = first["NUM_ALIAS"]
        num_derivative = first["NUM_DERIVATIVE"]

        pos_row = fetch_one("""
            SELECT ENG_POS
            FROM part_of_speech
            WHERE NUM_PART_OF_SPEECH = %s
        """, (first["NUM_PART_OF_SPEECH"],))
        pos_value = pos_row["ENG_POS"] if pos_row and pos_row["ENG_POS"] else "noun"

        lexical_entry = ET.SubElement(
            lexicon,
            "LexicalEntry",
            {"partOfSpeech": safe_str(pos_value)}
        )

        prolexeme_row = fetch_one(f"""
            SELECT LABEL_PROLEXEME, WIKIPEDIA_LINK
            FROM `prolexeme_{lang}`
            WHERE NUM_PROLEXEME = %s
        """, (num_prolexeme,))

        alias_row = None
        derivative_row = None

        if num_alias is not None:
            alias_row = fetch_one(f"""
                SELECT alias_category.ENG_CATEGORY, `alias_{lang}`.LABEL_ALIAS
                FROM `alias_{lang}`, alias_category
                WHERE `alias_{lang}`.NUM_ALIAS = %s
                  AND alias_category.NUM_ALIAS_CATEGORY = `alias_{lang}`.NUM_ALIAS_CATEGORY
            """, (num_alias,))

        if num_derivative is not None:
            derivative_row = fetch_one(f"""
                SELECT derivative_category.ENG_CATEGORY,
                       `derivative_{lang}`.LABEL_DERIVATIVE,
                       `derivative_{lang}`.`NUM_ALIAS-ETYMOLOGY`,
                       `derivative_{lang}`.`NUM_DERIVATIVE-ETYMOLOGY`
                FROM `derivative_{lang}`, derivative_category
                WHERE `derivative_{lang}`.NUM_DERIVATIVE = %s
                  AND derivative_category.NUM_DERIVATIVE_CATEGORY = `derivative_{lang}`.NUM_DERIVATIVE_CATEGORY
            """, (num_derivative,))

        if num_derivative is not None and derivative_row:
            lemma_text = derivative_row["LABEL_DERIVATIVE"]
        elif num_alias is not None and alias_row:
            lemma_text = alias_row["LABEL_ALIAS"]
        else:
            lemma_text = prolexeme_row["LABEL_PROLEXEME"] if prolexeme_row else ""

        ET.SubElement(lexical_entry, "Lemma").text = xml_escape(lemma_text)

        seen_wordforms = set()
        for inst in group:
            if inst["NUM_MORPHOLOGY"] is not None:
                morph_row = fetch_one(f"""
                    SELECT *
                    FROM `morphology_{lang}`
                    WHERE NUM_MORPHOLOGY = %s
                """, (inst["NUM_MORPHOLOGY"],))
            else:
                morph_row = None

            wf_attrs = build_morphology_attrs(morph_row)

            form_text = safe_str(inst["LABEL_INSTANCE"])
            wf_key = (tuple(sorted(wf_attrs.items())), form_text)
            if wf_key in seen_wordforms:
                continue
            seen_wordforms.add(wf_key)

            word_form = ET.SubElement(lexical_entry, "WordForm", wf_attrs)
            ET.SubElement(word_form, "FormRepresentation").text = xml_escape(form_text)

        # Sense
        if num_derivative is not None:
            sense_id = f"D{num_derivative}"
            term_provenance = derivative_row["ENG_CATEGORY"] if derivative_row else "relationalName"
            label = "derivative"
            sense_attrs = {
                "idSense": sense_id,
                "refSenseAxis": safe_str(num_pivot),
                "termProvenance": safe_str(term_provenance),
                "label": label,
                "refSense": f"P{num_prolexeme}"
            }
        elif num_alias is not None:
            sense_id = f"A{num_alias}"
            term_provenance = alias_row["ENG_CATEGORY"] if alias_row else "shortForm"
            label = "properName"
            sense_attrs = {
                "idSense": sense_id,
                "refSenseAxis": safe_str(num_pivot),
                "termProvenance": safe_str(term_provenance),
                "label": label
            }
        else:
            sense_id = f"P{num_prolexeme}"
            sense_attrs = {
                "idSense": sense_id,
                "refSenseAxis": safe_str(num_pivot),
                "termProvenance": "fullForm",
                "label": "properName"
            }

        sense = ET.SubElement(lexical_entry, "Sense", sense_attrs)

        # -------------------------------------------------
        # FREQUENCY PAR ANNEE -> MonolingualExternalRef
        # -------------------------------------------------
        yearly_frequency_table = f"frequency_{lang}"
        if table_exists(yearly_frequency_table):
            try:
                rows = fetch_all(f"""
                    SELECT fr.NUM_PROLEXEME,
                           fr.NUM_YEAR_FREQUENCY,
                           fr.NUM_FREQUENCY,
                           f.ENG_FREQUENCY
                    FROM `{yearly_frequency_table}` AS fr
                    JOIN frequency AS f
                      ON fr.NUM_FREQUENCY = f.NUM_FREQUENCY
                    WHERE fr.NUM_PROLEXEME = %s
                    ORDER BY fr.NUM_YEAR_FREQUENCY DESC
                """, (num_prolexeme,))

                for r in rows:
                    if r["NUM_YEAR_FREQUENCY"] is not None and r["ENG_FREQUENCY"] is not None:
                        year_value = 2000 + int(r["NUM_YEAR_FREQUENCY"])

                        ET.SubElement(
                            sense,
                            "MonolingualExternalRef",
                            {
                                "externalReference": safe_str(year_value),
                                "frequency": normalize_frequency_label(r["ENG_FREQUENCY"])
                            }
                        )
            except Exception as e:
                print(f"Erreur fréquence pour prolexème {num_prolexeme} ({lang}) : {e}")
        else:
            try:
                freq_row = fetch_one(f"""
                    SELECT frequency.ENG_FREQUENCY
                    FROM `prolexeme_{lang}`, frequency
                    WHERE `prolexeme_{lang}`.NUM_FREQUENCY = frequency.NUM_FREQUENCY
                      AND NUM_PIVOT = %s
                """, (num_pivot,))
                if freq_row and freq_row.get("ENG_FREQUENCY"):
                    ET.SubElement(
                        sense,
                        "MonolingualExternalRef",
                        {
                            "externalReference": VERSION,
                            "frequency": normalize_frequency_label(freq_row["ENG_FREQUENCY"])
                        }
                    )
            except Exception:
                pass

        # Wikipedia
        if prolexeme_row and prolexeme_row.get("WIKIPEDIA_LINK"):
            ET.SubElement(
                sense,
                "MonolingualExternalRef",
                {
                    "externalSystem": "Wikipedia",
                    "externalReference": wikipedia_base + safe_str(prolexeme_row["WIKIPEDIA_LINK"])
                }
            )

        # SyntacticBehaviour : classifying contexts
        rows = fetch_all(f"""
            SELECT `LABEL_CLASSIFYING_CONTEXT`, `classifying_context_{lang}`.`NUM_CLASSIFYING_CONTEXT`
            FROM `context_{lang}`, `classifying_context_{lang}`
            WHERE NUM_PIVOT = %s
              AND `context_{lang}`.`NUM_CLASSIFYING_CONTEXT` = `classifying_context_{lang}`.`NUM_CLASSIFYING_CONTEXT`
        """, (num_pivot,))
        for row in rows:
            frame_id = f"CC{row['NUM_CLASSIFYING_CONTEXT']}"
            ET.SubElement(
                sense,
                "SyntacticBehaviour",
                {"refSubcategorizationFrame": frame_id}
            )

        # SyntacticBehaviour : accessibility contexts
        rows = fetch_all(f"""
            SELECT accessibility.NUM_ACCESSIBILITY,
                   `LABEL_ACCESSIBILITY_CONTEXT`,
                   `accessibility_context_{lang}`.`NUM_ACCESSIBILITY_CONTEXT`
            FROM accessibility, `accessibility_{lang}`, `accessibility_context_{lang}`
            WHERE `NUM_PIVOT-ARGUMENT1` = %s
              AND accessibility.NUM_ACCESSIBILITY = `accessibility_{lang}`.NUM_ACCESSIBILITY
              AND `accessibility_context_{lang}`.NUM_ACCESSIBILITY_CONTEXT = `accessibility_{lang}`.NUM_ACCESSIBILITY_CONTEXT
        """, (num_pivot,))
        for row in rows:
            frame_id = f"AC{row['NUM_ACCESSIBILITY_CONTEXT']}"
            ET.SubElement(
                sense,
                "SyntacticBehaviour",
                {
                    "refSenseAxisRelation": safe_str(row["NUM_ACCESSIBILITY"]),
                    "refSubcategorizationFrame": frame_id
                }
            )

        # SyntacticBehaviour : collocations alias ou prolexème
        if num_alias is not None:
            rows = fetch_all(f"""
                SELECT `LABEL_COLLOCATION`, `collocation_{lang}`.`NUM_COLLOCATION`, `ENG_CATEGORY`
                FROM `collocation_{lang}`, `collocation_alias_{lang}`, `collocation_category`
                WHERE `collocation_{lang}`.NUM_COLLOCATION = `collocation_alias_{lang}`.NUM_COLLOCATION
                  AND `collocation_alias_{lang}`.NUM_ALIAS = %s
                  AND `collocation_category`.NUM_COLLOCATION_CATEGORY = `collocation_{lang}`.NUM_COLLOCATION_CATEGORY
            """, (num_alias,))
        else:
            rows = fetch_all(f"""
                SELECT `LABEL_COLLOCATION`, `collocation_{lang}`.`NUM_COLLOCATION`, `ENG_CATEGORY`
                FROM `collocation_{lang}`, `collocation_prolexeme_{lang}`, `collocation_category`
                WHERE `collocation_{lang}`.NUM_COLLOCATION = `collocation_prolexeme_{lang}`.NUM_COLLOCATION
                  AND NUM_PIVOT = %s
                  AND `collocation_category`.NUM_COLLOCATION_CATEGORY = `collocation_{lang}`.NUM_COLLOCATION_CATEGORY
            """, (num_pivot,))

        for row in rows:
            frame_id = f"CO{row['NUM_COLLOCATION']}"
            ET.SubElement(
                sense,
                "SyntacticBehaviour",
                {"refSubcategorizationFrame": frame_id}
            )

        get_or_create_sense_axis(num_pivot)

    # -------------------------------------------------
    # SubcategorizationFrame du lexique
    # -------------------------------------------------
    if lang_pivots:
        placeholders = ", ".join(["%s"] * len(lang_pivots))
        pivot_params = tuple(lang_pivots)

        colloc_rows = []
        if table_exists(f"collocation_{lang}") and table_exists(f"collocation_category") and (table_exists(f"collocation_prolexeme_{lang}") or table_exists(f"collocation_alias_{lang}")):
            colloc_rows = fetch_all(f"""
            SELECT `NUM_COLLOCATION`, `LABEL_COLLOCATION`, `ENG_CATEGORY`
            FROM `collocation_{lang}`, `collocation_category`
            WHERE `collocation_category`.NUM_COLLOCATION_CATEGORY = `collocation_{lang}`.NUM_COLLOCATION_CATEGORY
              AND (
                  `collocation_{lang}`.NUM_COLLOCATION IN (
                      SELECT `NUM_COLLOCATION`
                      FROM `collocation_prolexeme_{lang}`
                      WHERE NUM_PIVOT IN ({placeholders})
                  )
                  OR
                  `collocation_{lang}`.NUM_COLLOCATION IN (
                      SELECT `NUM_COLLOCATION`
                      FROM `collocation_alias_{lang}`
                      WHERE NUM_ALIAS IN (
                          SELECT DISTINCT NUM_ALIAS FROM `instance_{lang}`
                      )
                  )
              )
        """, pivot_params)

        for row in colloc_rows:
            add_unique_subcategorization_frame(
                lexicon,
                subcat_frames_created,
                f"CO{row['NUM_COLLOCATION']}",
                text=row["LABEL_COLLOCATION"],
                attrs={"introducer": safe_str(row["ENG_CATEGORY"])}
            )

        class_rows = []
        if table_exists(f"classifying_context_{lang}") and table_exists(f"context_{lang}") and table_exists(f"morphology_{lang}"):
            class_rows = fetch_all(f"""
            SELECT cc.`NUM_CLASSIFYING_CONTEXT`,
                   cc.`LABEL_CLASSIFYING_CONTEXT`,
                   cc.`RESTRICTION`,
                   m.`GENDER`,
                   m.`NUMBER`
            FROM `classifying_context_{lang}` AS cc
            LEFT JOIN `morphology_{lang}` AS m
              ON cc.NUM_MORPHOLOGY = m.NUM_MORPHOLOGY
            WHERE cc.NUM_CLASSIFYING_CONTEXT IN (
                  SELECT `NUM_CLASSIFYING_CONTEXT`
                  FROM `context_{lang}`
                  WHERE NUM_PIVOT IN ({placeholders})
              )
        """, pivot_params)

        for row in class_rows:
            attrs = {"introducer": "classifyingContext"}
            if row.get("GENDER") is not None:
                attrs["grammaticalGender"] = safe_str(row["GENDER"])
            if row.get("NUMBER") is not None:
                attrs["grammaticalNumber"] = safe_str(row["NUMBER"])
            if row["RESTRICTION"] != 1 and row["RESTRICTION"] is not None:
                attrs["restrictionRank"] = safe_str(row["RESTRICTION"])

            add_unique_subcategorization_frame(
                lexicon,
                subcat_frames_created,
                f"CC{row['NUM_CLASSIFYING_CONTEXT']}",
                text=row["LABEL_CLASSIFYING_CONTEXT"],
                attrs=attrs
            )

        access_rows = []
        if table_exists(f"accessibility_context_{lang}") and table_exists(f"accessibility_{lang}") and table_exists("accessibility") and table_exists(f"morphology_{lang}"):
            access_rows = fetch_all(f"""
            SELECT ac.`NUM_ACCESSIBILITY_CONTEXT`,
                   ac.`LABEL_ACCESSIBILITY_CONTEXT`,
                   ac.`RESTRICTION`,
                   m.`GENDER`,
                   m.`NUMBER`
            FROM `accessibility_context_{lang}` AS ac
            LEFT JOIN `morphology_{lang}` AS m
              ON ac.NUM_MORPHOLOGY = m.NUM_MORPHOLOGY
            WHERE ac.NUM_ACCESSIBILITY_CONTEXT IN (
                  SELECT `NUM_ACCESSIBILITY_CONTEXT`
                  FROM `accessibility_{lang}`
                  WHERE NUM_ACCESSIBILITY IN (
                      SELECT NUM_ACCESSIBILITY
                      FROM accessibility
                      WHERE `NUM_PIVOT-ARGUMENT1` IN ({placeholders})
                  )
              )
        """, pivot_params)

        for row in access_rows:
            attrs = {"introducer": "accessibilityContext"}
            if row.get("GENDER") is not None:
                attrs["grammaticalGender"] = safe_str(row["GENDER"])
            if row.get("NUMBER") is not None:
                attrs["grammaticalNumber"] = safe_str(row["NUMBER"])
            if row["RESTRICTION"] != 1 and row["RESTRICTION"] is not None:
                attrs["restrictionRank"] = safe_str(row["RESTRICTION"])

            add_unique_subcategorization_frame(
                lexicon,
                subcat_frames_created,
                f"AC{row['NUM_ACCESSIBILITY_CONTEXT']}",
                text=row["LABEL_ACCESSIBILITY_CONTEXT"],
                attrs=attrs
            )

# -------------------------------------------------
# SenseAxis globaux à la fin
# -------------------------------------------------
for pivot_id in sorted(sense_axes.keys()):
    lexical_resource.append(sense_axes[pivot_id])

# -------------------------------------------------
# EXPORT
# -------------------------------------------------
with open(XML_OUTPUT, "w", encoding="utf-8") as f:
    f.write(prettify_xml(lexical_resource))

cursor.close()
conn.close()

print(f"Fichier généré : {XML_OUTPUT}")