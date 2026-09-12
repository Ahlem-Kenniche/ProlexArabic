#!/usr/bin/env python3
"""Validate a ProLMF XML file against the bundled XSD schema."""
from pathlib import Path
import argparse
import sys
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_XSD = ROOT / "prolmf" / "ProLMF_4.xsd"
DEFAULT_XML = ROOT / "outputs" / "sample_prolmf_excerpt.xml"

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xsd", type=Path, default=DEFAULT_XSD, help="Path to ProLMF XSD")
    parser.add_argument("--xml", type=Path, default=DEFAULT_XML, help="Path to XML file")
    args = parser.parse_args()
    try:
        schema_doc = etree.parse(str(args.xsd))
        schema = etree.XMLSchema(schema_doc)
        xml_doc = etree.parse(str(args.xml))
        schema.assertValid(xml_doc)
        print(f"VALID: {args.xml}")
    except OSError as exc:
        print(f"FILE ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
    except etree.DocumentInvalid as exc:
        print(f"INVALID XML: {exc}", file=sys.stderr)
        raise SystemExit(2)
    except (etree.XMLSyntaxError, etree.XMLSchemaParseError) as exc:
        print(f"XML/XSD ERROR: {exc}", file=sys.stderr)
        raise SystemExit(3)

if __name__ == "__main__":
    main()
