"""Download PrimeKG, keep the clinical slice, and load it into Neo4j."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cdss.config import get_settings
from cdss.graph.load import ensure_source_files, filter_primekg, load_into_neo4j


def main() -> None:
    settings = get_settings()
    nodes, edges = ensure_source_files(settings.primekg_dir)
    summary = filter_primekg(nodes, edges, settings.primekg_dir)
    print(summary)
    if not settings.neo4j_password:
        print("NEO4J_PASSWORD is empty. The clinical slice is on disk. Neo4j was not loaded.")
        return
    load_into_neo4j(settings.primekg_dir, settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    print("Neo4j load finished.")


if __name__ == "__main__":
    main()
