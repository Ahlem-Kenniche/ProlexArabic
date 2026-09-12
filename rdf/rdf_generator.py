import mysql.connector
import yaml
from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, RDFS, XSD, OWL
from rdflib.namespace import SKOS
import logging
import argparse
from pathlib import Path

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# ✔ IMPORTANT : namespace OWL correct
PROLEX = Namespace("https://example.org/prolexbase/ontology#")
ONTOLEX = Namespace("http://www.w3.org/ns/lemon/ontolex#")


def uri(name):
    return PROLEX[name]


def query(cur, sql):
    cur.execute(sql)
    return cur.fetchall()


def table_exists(cur, table):
    cur.execute("""
        SELECT COUNT(*) AS cnt
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
        AND table_name = %s
    """, (table,))
    
    row = cur.fetchone()
    return row["cnt"] == 1

def table_nonempty(cur, table):
    try:
        cur.execute(f"SELECT 1 FROM `{table}` LIMIT 1")
        return cur.fetchone() is not None
    except Exception as e:
        log.warning(f"Table {table} inaccessible: {e}")
    return False
        

class Converter:

    LANG_SUFFIX = {
        "arb": "ar",
        "arz": "arz",
        "fra": "fr",
        "eng": "en",
        "deu": "de",
        "nld": "nl",
        "pol": "pl",
        "por": "pt",
        "spa": "es",
        "srp": "sr",
        "ita": "it",
        "kor": "ko",
        "wol": "wo"
    }
    def __init__(self, config_path="config.yaml"):
        self.g = Graph()
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {config_file}. "
                "Copy config.example.yaml to config.yaml and edit the database credentials."
            )

        with config_file.open("r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        self.output_file = config.get("output", {}).get("rdf_file", "rdf/prolexbase-full.ttl")

        self.conn = mysql.connector.connect(
            host=config["database"]["host"],
            user=config["database"]["user"],
            password=config["database"]["password"],
            database=config["database"]["name"]
        )

        self.cur = self.conn.cursor(dictionary=True)
        self.years = {}
        self.language_ids = {}
        self.g.bind("prolex", PROLEX)
        self.g.bind("ontolex", ONTOLEX)
        self.g.bind("rdf", RDF)
        self.g.bind("rdfs", RDFS)
        self.g.bind("owl", OWL)
        self.g.bind("skos", SKOS)

    #pivot
    def convert_pivot(self):
        for r in query(self.cur, "SELECT * FROM pivot"):

            pivot = uri(f"Pivot_{r['NUM_PIVOT']}")
            self.g.add((pivot, RDF.type, PROLEX.Pivot))

            if r.get("NUM_TYPE"):
                t = uri(f"Type_{r['NUM_TYPE']}")
                self.g.add((pivot, PROLEX.hasType, t))
                
            self.g.add((pivot, RDFS.label, Literal(f"Pivot_{r['NUM_PIVOT']}")))  

    # type
    def convert_type(self):
        for r in query(self.cur, "SELECT * FROM type"):

            t = uri(f"Type_{r['NUM_TYPE']}")
            self.g.add((t, RDF.type, PROLEX.Type))

            label = r.get("ENG_TYPE") or r.get("FRA_TYPE")

            if label:
               if r.get("ENG_TYPE"):
                self.g.add((
                        t,
                        PROLEX.typeLabel,
                        Literal(r["ENG_TYPE"], lang="en")
                    ))

                if r.get("FRA_TYPE"):
                    self.g.add((
                        t,
                        PROLEX.typeLabel,
                        Literal(r["FRA_TYPE"], lang="fr")
                    ))
    # LANGUAGE
    def convert_language(self):

        for r in query(self.cur, "SELECT * FROM language"):

            iso = r.get("ISO_CODE")
            if not iso:
                continue
            self.language_ids[r["NUM_LANGUAGE"]] = iso

            lang = uri(f"Language_{iso}")

            self.g.add((lang, RDF.type, PROLEX.Language))
            self.g.add((lang, PROLEX.languageISO, Literal(iso)))

            if r.get("ENG_LANGUAGE"):
                self.g.add((
                    lang,
                    PROLEX.languageName,
                    Literal(r["ENG_LANGUAGE"], lang="en")
                ))

            if r.get("NUM_SCRIPT"):
                script = uri(f"Script_{r['NUM_SCRIPT']}")
                self.g.add((lang, PROLEX.hasScript, script))

    #SCRIPT
    def convert_script(self):
        for r in query(self.cur, "SELECT * FROM script"):
            script = uri(f"Script_{r['NUM_SCRIPT']}")
            self.g.add((script, RDF.type, PROLEX.Script))
            if r.get("ENG_SCRIPT"):
                self.g.add((
                script,
                PROLEX.scriptName,
                Literal(r["ENG_SCRIPT"], lang="en")
            ))

            if r.get("FRA_SCRIPT"):
                self.g.add((
                script,
                PROLEX.scriptName,
                Literal(r["FRA_SCRIPT"], lang="fr")
            ))

    #  DIALECT 
    def convert_dialect(self):
        for r in query(self.cur, "SELECT * FROM dialect"):

            d = uri(f"Dialect_{r['NUM_DIALECT']}")
            self.g.add((d, RDF.type, PROLEX.Dialect))
            if r.get("ENG_DIALECT"):
                self.g.add((
                    d,
                    RDFS.label,
                    Literal(r["ENG_DIALECT"], lang="en")
                ))

            if r.get("FRA_DIALECT"):
                self.g.add((
                    d,
                    RDFS.label,
                    Literal(r["FRA_DIALECT"], lang="fr")
                ))

            if r.get("NUM_LANGUAGE"):
                iso = self.language_ids.get(r["NUM_LANGUAGE"])

                if iso:
                    lang = uri(f"Language_{iso}")
                    
                    self.g.add((d, PROLEX.isDialectOf, lang))
                

    # ALIAS CATEGORY 
    def convert_aliasCategory(self):
        for r in query(self.cur, "SELECT * FROM alias_category"):

            a = uri(f"AliasCategory_{r['NUM_ALIAS_CATEGORY']}")
            self.g.add((a, RDF.type, PROLEX.AliasCategory))

    #  LEXICAL ENTRIES 
    def convert_lexical_entries(self):

        prefixes = ["prolexeme", "alias", "instance",
                     "derivative", "idiom", "terminology"]
        
        class_map = {
            "prolexeme": PROLEX.Prolexeme,
            "alias": PROLEX.Alias,
            "instance": PROLEX.Instance,
            "derivative": PROLEX.Derivative,
            "idiom": PROLEX.Idiom,
            "terminology": PROLEX.Terminology
        }

        for prefix in prefixes:
            for suffix, lang_code in self.LANG_SUFFIX.items():

                table = f"{prefix}_{suffix}"

                if not table_exists(self.cur, table):
                    continue

                for r in query(self.cur, f"SELECT * FROM {table}"):

                    id_val = (
                        r.get("NUM_PROLEXEME") or
                        r.get("NUM_ALIAS") or
                        r.get("NUM_INSTANCE") or
                        r.get("NUM_DERIVATIVE") or
                        r.get("NUM_IDIOM") or
                        r.get("NUM_TERMINOLOGY")
                    )

                    if not id_val:
                        continue

                    le = uri(f"LexicalEntry_{prefix}_{suffix}_{id_val}")
                    self.g.add((le, RDF.type, PROLEX.LexicalEntry))
                    self.g.add((le, RDF.type, class_map[prefix]))
                    self.g.add((
                        le,
                        PROLEX.lexicalType,
                        Literal(prefix)
                    ))
                    label_map = {
                         "prolexeme": "LABEL_PROLEXEME",
                         "alias": "LABEL_ALIAS",
                         "instance": "LABEL_INSTANCE",
                         "derivative": "LABEL_DERIVATIVE",
                         "idiom": "LABEL_IDIOM",
                         "terminology": "LABEL_TERMINOLOGY"
                        }

                    field = label_map[prefix]
                    label = r.get(field)
                    

                    # 1. toujours créer la Form
                    form = uri(f"Form_{prefix}_{suffix}_{id_val}")
                    self.g.add((form, RDF.type, ONTOLEX.Form))

                    # 2. writtenRep seulement si label existe
                    if label:
                        self.g.add((
                            form,
                            ONTOLEX.writtenRep,
                            Literal(label, lang=lang_code)
                        ))

                    # 3. type de forme
                    self.g.add((form, PROLEX.formType, Literal(prefix)))

                    # 4. attachement OntoLex
                    if prefix == "prolexeme":
                        self.g.add((le, ONTOLEX.canonicalForm, form))
                    else:
                        self.g.add((le, ONTOLEX.otherForm, form))
                        if label:
                            self.g.add((le, PROLEX.lexicalLabel, Literal(label, lang=lang_code)))
                            self.g.add((le, RDFS.label, Literal(label, lang=lang_code)))
                    # hasLanguage
                    lang = uri(f"Language_{suffix}")
                    self.g.add((le, PROLEX.hasLanguage, lang))
                    

                    # isLexicalEntryOf + inverse hasLexicalEntry
                    if r.get("NUM_PIVOT"):
                        pivot = uri(f"Pivot_{r['NUM_PIVOT']}")
                        self.g.add((le, PROLEX.isLexicalEntryOf, pivot))
                        self.g.add((pivot, PROLEX.hasLexicalEntry, le))

                    # hasAliasCategory
                    if r.get("NUM_ALIAS_CATEGORY"):
                        cat = uri(f"AliasCategory_{r['NUM_ALIAS_CATEGORY']}")
                        self.g.add((le, PROLEX.hasAliasCategory, cat))

                    # hasMorphology
                    if r.get("NUM_MORPHOLOGY"):
                        morph = uri(f"Morphology_{suffix}_{r['NUM_MORPHOLOGY']}")
                        self.g.add((morph, RDF.type, PROLEX.Morphology))
                        self.g.add((le, PROLEX.hasMorphology, morph))
                        

    # MERONYMY
    def convert_meronymy(self):

        if not table_exists(self.cur, "meronymy"):
            return

        for r in query(self.cur, "SELECT * FROM meronymy"):

            whole = uri(f"Pivot_{r['NUM_PIVOT-HOLONYMOUS']}")
            part = uri(f"Pivot_{r['NUM_PIVOT-MERONYMOUS']}")

            self.g.add((whole, PROLEX.hasMeronym, part))
            self.g.add((part, PROLEX.isPartOf, whole))

    # YEARS 
    def load_years(self):

        for r in query(self.cur, "SELECT * FROM year_frequency"):
            self.years[r["NUM_YEAR_FREQUENCY"]] = r.get("YEARNB")

    # TEMPORAL FREQUENCY 
    def convert_temporal_frequency(self):

        total = 0

        for suffix in self.LANG_SUFFIX:

            table = f"frequency_{suffix}"

            if not table_exists(self.cur, table):
                continue

            for r in query(self.cur, f"SELECT * FROM {table}"):

                if not r.get("NUM_PROLEXEME") or not r.get("NUM_YEAR_FREQUENCY"):
                    continue

                tf = uri(f"TF_{suffix}_{r['NUM_PROLEXEME']}_{r['NUM_YEAR_FREQUENCY']}")

                self.g.add((tf, RDF.type, PROLEX.TemporalFrequency))

                if r.get("NUM_FREQUENCY"):
                    self.g.add((tf, PROLEX.frequencyValue,
                                Literal(r["NUM_FREQUENCY"], datatype=XSD.float)))

                year = self.years.get(r["NUM_YEAR_FREQUENCY"])
                if year:
                    self.g.add((tf, PROLEX.yearValue,
                                Literal(year, datatype=XSD.integer)))

                le = uri(f"LexicalEntry_prolexeme_{suffix}_{r['NUM_PROLEXEME']}")
                self.g.add((le, PROLEX.hasTemporalFrequency, tf))
                

                total += 1

        log.info(f"TemporalFrequency  {total}")

    # ACCESSIBILITY
    def convert_accessibility(self):

        if not table_exists(self.cur, "accessibility"):
            return

        total = 0

        for r in query(self.cur, "SELECT * FROM accessibility"):

            p1 = r.get("NUM_PIVOT-ARGUMENT1")
            p2 = r.get("NUM_PIVOT-ARGUMENT2")

            if not p1 or not p2:
                continue

            pivot1 = uri(f"Pivot_{p1}")
            pivot2 = uri(f"Pivot_{p2}")

            self.g.add((pivot1, PROLEX.accessibleVia, pivot2))

            total += 1

        log.info(f"Accessibility  {total}")

    #  COLLOCATION 
    def convert_collocation(self):

        total = 0

        for suffix in self.LANG_SUFFIX:

            table = f"collocation_{suffix}"

            if not table_exists(self.cur, table):
                continue

            for r in query(self.cur, f"SELECT * FROM {table}"):

                if not r.get("NUM_COLLOCATION"):
                    continue

                colloc = uri(f"Collocation_{suffix}_{r['NUM_COLLOCATION']}")
                self.g.add((colloc, RDF.type, PROLEX.Collocation))

                if r.get("LABEL_COLLOCATION"):

                    self.g.add((
                        colloc,
                        PROLEX.collocationLabel,
                        Literal(
                            r["LABEL_COLLOCATION"],
                            lang=self.LANG_SUFFIX[suffix]
                        )
                    ))

                    self.g.add((
                        colloc,
                        RDFS.label,
                        Literal(
                            r["LABEL_COLLOCATION"],
                            lang=self.LANG_SUFFIX[suffix]
                        )
                    ))
                if r.get("NUM_PIVOT"):
                    pivot = uri(f"Pivot_{r['NUM_PIVOT']}")
                    self.g.add((pivot, PROLEX.hasCollocation, colloc))

                total += 1

        log.info(f"Collocation {total}")

    # MORPHOLOGY 
    def convert_morphology(self):

        total = 0

        for suffix in self.LANG_SUFFIX:

            table = f"morphology_{suffix}"

            if not table_exists(self.cur, table):
                continue

            for r in query(self.cur, f"SELECT * FROM {table}"):

                id_morph = r.get("NUM_MORPHOLOGY") 
                if not id_morph:
                    continue

                morph = uri(f"Morphology_{suffix}_{id_morph}")
                self.g.add((morph, RDF.type, PROLEX.Morphology))

                if r.get("GENDER"):
                    self.g.add((morph, PROLEX.genderValue, Literal(r["GENDER"])))
                if r.get("NUMBER"):
                    self.g.add((morph, PROLEX.numberValue, Literal(r["NUMBER"])))
                if r.get("PERSON"):
                    self.g.add((morph, PROLEX.personValue, Literal(r["PERSON"])))
                if r.get("TAM"):
                    self.g.add((morph, PROLEX.tamValue, Literal(r["TAM"])))

                total += 1

        log.info(f"Morphology  {total}")

    #  ACCESSIBILITY CONTEXT 
    def convert_accessibility_context(self):

        total = 0

        for suffix in self.LANG_SUFFIX:

            table = f"accessibility_context_{suffix}"

            if not table_exists(self.cur, table):
                continue

            for r in query(self.cur, f"SELECT * FROM {table}"):

                if not r.get("NUM_ACCESSIBILITY_CONTEXT"):
                    continue

                ctx = uri(f"AccessibilityContext_{suffix}_{r['NUM_ACCESSIBILITY_CONTEXT']}")
                self.g.add((ctx, RDF.type, PROLEX.AccessibilityContext))
                if r.get("NUM_MORPHOLOGY"):
                    morph = uri(f"Morphology_{suffix}_{r['NUM_MORPHOLOGY']}")
                    self.g.add((ctx, PROLEX.hasMorphologyConstraint, morph))

                if r.get("LABEL_ACCESSIBILITY_CONTEXT"):
                    self.g.add((
                        ctx,
                        RDFS.label,
                        Literal(
                            r["LABEL_ACCESSIBILITY_CONTEXT"],
                            lang=self.LANG_SUFFIX[suffix]
                        )
                    ))
                   
                if r.get("RESTRICTION") is not None:
                    self.g.add((ctx, PROLEX.restrictionValue,
                                Literal(r["RESTRICTION"])))

                total += 1

        log.info(f"AccessibilityContext {total}")
        # SYNONYMY 
    def convert_synonymy(self):

        if not table_exists(self.cur, "synonymy"):
            return

        total = 0

        for r in query(self.cur, "SELECT * FROM synonymy"):

            p1 = r.get("NUM_PIVOT-CANONICAL")
            p2 = r.get("NUM_PIVOT-SYNONYMOUS")

            if not p1 or not p2:
                continue

            pivot1 = uri(f"Pivot_{p1}")
            pivot2 = uri(f"Pivot_{p2}")

            self.g.add((pivot1, PROLEX.hasSynonym, pivot2))
            self.g.add((pivot1, SKOS.closeMatch, pivot2))

            total += 1

        log.info(f"Synonymy  {total}")
#  DECLAREOWL SCHEMA 
    def declare_owl_schema(self):

    #  CLASSES 
        classes = [

        PROLEX.Pivot,
        PROLEX.Type,
        PROLEX.Language,
        PROLEX.Script,
        PROLEX.Dialect,
        PROLEX.LexicalEntry,
        PROLEX.Prolexeme,
        PROLEX.Alias,
        PROLEX.Instance,
        PROLEX.Derivative,
        PROLEX.Idiom,
        PROLEX.Terminology,
        PROLEX.Morphology,
        PROLEX.Collocation,
        PROLEX.AccessibilityContext,
        PROLEX.TemporalFrequency,
        PROLEX.AliasCategory

        ]

        for c in classes:
            self.g.add((c, RDF.type, OWL.Class))

    #  OBJECT PROPERTIES
        object_properties = [

            ("hasType", PROLEX.Pivot, PROLEX.Type),

            ("hasLexicalEntry", PROLEX.Pivot, PROLEX.LexicalEntry),

            ("isLexicalEntryOf", PROLEX.LexicalEntry, PROLEX.Pivot),

            ("hasLanguage", PROLEX.LexicalEntry, PROLEX.Language),

            ("hasScript", PROLEX.Language, PROLEX.Script),

            ("isDialectOf", PROLEX.Dialect, PROLEX.Language),

            ("hasAliasCategory", PROLEX.LexicalEntry, PROLEX.AliasCategory),

            ("hasMorphology", PROLEX.LexicalEntry, PROLEX.Morphology),


            ("hasTemporalFrequency", PROLEX.LexicalEntry, PROLEX.TemporalFrequency),

            ("hasMeronym", PROLEX.Pivot, PROLEX.Pivot),

            ("isPartOf", PROLEX.Pivot, PROLEX.Pivot),

            ("hasCollocation", PROLEX.Pivot, PROLEX.Collocation),
            
            ("hasSynonym", PROLEX.Pivot, PROLEX.Pivot),

            ("accessibleVia", PROLEX.Pivot, PROLEX.Pivot),

            ("hasMorphologyConstraint", PROLEX.AccessibilityContext, PROLEX.Morphology)
        ]

        for prop, domain, range_ in object_properties:

            p = PROLEX[prop]

            self.g.add((p, RDF.type, OWL.ObjectProperty))
            self.g.add((p, RDFS.domain, domain))
            self.g.add((p, RDFS.range, range_))

        # DATATYPE PROPERTIES 
        datatype_properties = [

            ("lexicalLabel", PROLEX.LexicalEntry, XSD.string),

            ("typeLabel", PROLEX.Type, XSD.string),

            ("languageISO", PROLEX.Language, XSD.string),

            ("languageName", PROLEX.Language, XSD.string),

            ("scriptName", PROLEX.Script, XSD.string),

            ("lexicalType", PROLEX.LexicalEntry, XSD.string),

            ("frequencyValue", PROLEX.TemporalFrequency, XSD.float),

            ("yearValue", PROLEX.TemporalFrequency, XSD.integer),

            ("genderValue", PROLEX.Morphology, XSD.string),

            ("numberValue", PROLEX.Morphology, XSD.string),

            ("personValue", PROLEX.Morphology, XSD.string),

            ("tamValue", PROLEX.Morphology, XSD.string),

            ("restrictionValue", PROLEX.AccessibilityContext, XSD.string),

            ("collocationLabel", PROLEX.Collocation, XSD.string)
        ]

        for prop, domain , range_ in datatype_properties:

            p = PROLEX[prop]

            self.g.add((p, RDF.type, OWL.DatatypeProperty))
            self.g.add((p, RDFS.domain, domain))
            self.g.add((p, RDFS.range, range_))
        #  EXPORT 
    def export_rdf(self, file=None):
        file = file or self.output_file
        output_path = Path(file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.g.serialize(destination=str(output_path), format="turtle")
        print("RDF generated:", output_path)


def main():
    parser = argparse.ArgumentParser(description="Convert Prolexbase MySQL data to RDF/Turtle.")
    parser.add_argument("--config", default="config.yaml", help="Path to the local YAML configuration file.")
    parser.add_argument("--output", default=None, help="Optional output Turtle file. Overrides config output.rdf_file.")
    args = parser.parse_args()

    conv = None
    try:
        conv = Converter(config_path=args.config)
        conv.convert_pivot()
        conv.convert_type()
        conv.convert_language()
        conv.convert_script()
        conv.convert_dialect()
        conv.convert_aliasCategory()
        conv.convert_lexical_entries()
        conv.convert_meronymy()
        conv.load_years()
        conv.convert_temporal_frequency()
        conv.convert_collocation()
        conv.convert_morphology()
        conv.convert_accessibility_context()
        conv.convert_accessibility()
        conv.convert_synonymy()
        conv.declare_owl_schema()
        conv.export_rdf(args.output)
    finally:
        if conv:
            conv.cur.close()
            conv.conn.close()


if __name__ == "__main__":
    main()









