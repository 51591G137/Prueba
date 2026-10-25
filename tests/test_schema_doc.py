"""Comprueba que docs/schema.dbml describe las mismas tablas, columnas y borrados que los modelos.

Uso (desde la raíz del repositorio):  python tests/test_schema_doc.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from backend import create_app  # noqa: E402
from backend.core.extensions import db  # noqa: E402


def read_dbml():
    tables, refs = {}, {}
    current, in_block = None, False
    for raw in open(os.path.join(ROOT, "docs", "schema.dbml"), encoding="utf-8"):
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        match = re.match(r"Table (\w+) \{", line)
        if match:
            current, in_block = match.group(1), False
            tables[current] = set()
            continue
        ref = re.match(r"Ref: (\w+)\.(\w+) > (\w+)\.(\w+) \[delete: (cascade|set null)\]", line)
        if ref:
            refs[(ref.group(1), ref.group(2))] = (ref.group(3), ref.group(5).upper())
            continue
        if current is None:
            continue
        if line.startswith("indexes {"):
            in_block = True
        elif in_block:
            in_block = line != "}"
        elif line == "}":
            current = None
        else:
            tables[current].add(line.split()[0])
    return tables, refs


def main():
    app = create_app({"DATABASE_URL": "sqlite://", "AUTO_MIGRATE": False})
    with app.app_context():
        model_tables = {name: {c.name for c in table.columns} for name, table in db.metadata.tables.items()}
        model_refs = {}
        for name, table in db.metadata.tables.items():
            for fk in table.foreign_keys:
                model_refs[(name, fk.parent.name)] = (fk.column.table.name, (fk.ondelete or "NO ACTION").upper())
    doc_tables, doc_refs = read_dbml()
    problems = []
    for name in sorted(set(model_tables) | set(doc_tables)):
        if name not in doc_tables:
            problems.append(f"Falta en docs/schema.dbml la tabla «{name}»")
        elif name not in model_tables:
            problems.append(f"docs/schema.dbml tiene la tabla «{name}», que ya no existe en los modelos")
        elif model_tables[name] != doc_tables[name]:
            problems.append(f"Tabla «{name}»: columnas distintas. Solo en modelos: {sorted(model_tables[name] - doc_tables[name])}; solo en la documentación: {sorted(doc_tables[name] - model_tables[name])}")
    for key in sorted(set(model_refs) | set(doc_refs)):
        if model_refs.get(key) != doc_refs.get(key):
            problems.append(f"Relación {key[0]}.{key[1]}: modelos={model_refs.get(key)} documentación={doc_refs.get(key)}")
    if problems:
        print("docs/schema.dbml NO coincide con los modelos:")
        print("\n".join("  - " + p for p in problems))
        sys.exit(1)
    print(f"OK: docs/schema.dbml coincide con los modelos ({len(model_tables)} tablas, {len(model_refs)} relaciones)")


if __name__ == "__main__":
    main()
