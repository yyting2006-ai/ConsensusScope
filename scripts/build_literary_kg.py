from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "curated_literary_kg_v1"


CURATED_WORKS: List[Dict[str, object]] = [
    {
        "work": "Frankenstein",
        "aliases": ["Frankenstein; or, The Modern Prometheus"],
        "author": "Mary Shelley",
        "publication_year": "1818",
        "form": ["novel"],
        "genre": ["Gothic fiction", "science fiction"],
        "characters": ["Victor Frankenstein", "the creature"],
        "themes": ["ambition", "creation", "responsibility"],
    },
    {
        "work": "Jane Eyre",
        "aliases": [],
        "author": "Charlotte Bronte",
        "publication_year": "1847",
        "form": ["novel"],
        "genre": ["Bildungsroman", "Gothic fiction"],
        "characters": ["Jane Eyre", "Edward Rochester"],
        "themes": ["moral independence", "social class", "gender"],
    },
    {
        "work": "Pride and Prejudice",
        "aliases": [],
        "author": "Jane Austen",
        "publication_year": "1813",
        "form": ["novel"],
        "genre": ["novel of manners"],
        "characters": ["Elizabeth Bennet", "Fitzwilliam Darcy"],
        "themes": ["marriage", "class", "judgment"],
    },
    {
        "work": "Wuthering Heights",
        "aliases": [],
        "author": "Emily Bronte",
        "publication_year": "1847",
        "form": ["novel"],
        "genre": ["Gothic fiction"],
        "characters": ["Heathcliff", "Catherine Earnshaw"],
        "themes": ["revenge", "social class", "destructive love"],
    },
    {
        "work": "Hamlet",
        "aliases": ["The Tragedy of Hamlet"],
        "author": "William Shakespeare",
        "publication_year": "1603",
        "form": ["play"],
        "genre": ["tragedy"],
        "characters": ["Hamlet", "Claudius", "Ophelia"],
        "themes": ["revenge", "mortality", "uncertainty"],
    },
    {
        "work": "Macbeth",
        "aliases": ["The Tragedy of Macbeth"],
        "author": "William Shakespeare",
        "publication_year": "1606",
        "form": ["play"],
        "genre": ["tragedy"],
        "characters": ["Macbeth", "Lady Macbeth"],
        "themes": ["ambition", "guilt", "power"],
    },
    {
        "work": "Othello",
        "aliases": ["The Tragedy of Othello"],
        "author": "William Shakespeare",
        "publication_year": "1603",
        "form": ["play"],
        "genre": ["tragedy"],
        "characters": ["Othello", "Desdemona", "Iago"],
        "themes": ["jealousy", "race", "manipulation"],
    },
    {
        "work": "King Lear",
        "aliases": ["The Tragedy of King Lear"],
        "author": "William Shakespeare",
        "publication_year": "1606",
        "form": ["play"],
        "genre": ["tragedy"],
        "characters": ["King Lear", "Cordelia", "Goneril", "Regan"],
        "themes": ["authority", "family", "madness"],
    },
    {
        "work": "Great Expectations",
        "aliases": [],
        "author": "Charles Dickens",
        "publication_year": "1861",
        "form": ["novel"],
        "genre": ["Bildungsroman"],
        "characters": ["Pip", "Estella", "Miss Havisham"],
        "themes": ["class mobility", "guilt", "moral growth"],
    },
    {
        "work": "Oliver Twist",
        "aliases": [],
        "author": "Charles Dickens",
        "publication_year": "1838",
        "form": ["novel"],
        "genre": ["social novel"],
        "characters": ["Oliver Twist", "Fagin", "Nancy"],
        "themes": ["poverty", "childhood", "social injustice"],
    },
    {
        "work": "A Tale of Two Cities",
        "aliases": [],
        "author": "Charles Dickens",
        "publication_year": "1859",
        "form": ["novel"],
        "genre": ["historical novel"],
        "characters": ["Charles Darnay", "Sydney Carton", "Lucie Manette"],
        "themes": ["revolution", "sacrifice", "resurrection"],
    },
    {
        "work": "The Picture of Dorian Gray",
        "aliases": ["Dorian Gray"],
        "author": "Oscar Wilde",
        "publication_year": "1890",
        "form": ["novel"],
        "genre": ["philosophical fiction", "Gothic fiction"],
        "characters": ["Dorian Gray", "Lord Henry Wotton", "Basil Hallward"],
        "themes": ["aestheticism", "corruption", "art"],
    },
    {
        "work": "Dracula",
        "aliases": [],
        "author": "Bram Stoker",
        "publication_year": "1897",
        "form": ["novel"],
        "genre": ["Gothic fiction", "horror fiction"],
        "characters": ["Count Dracula", "Jonathan Harker", "Mina Harker"],
        "themes": ["fear", "modernity", "invasion"],
    },
    {
        "work": "The Strange Case of Dr Jekyll and Mr Hyde",
        "aliases": ["Strange Case of Dr Jekyll and Mr Hyde", "Jekyll and Hyde"],
        "author": "Robert Louis Stevenson",
        "publication_year": "1886",
        "form": ["novella"],
        "genre": ["Gothic fiction"],
        "characters": ["Dr Jekyll", "Mr Hyde", "Gabriel Utterson"],
        "themes": ["duality", "respectability", "repression"],
    },
    {
        "work": "Moby-Dick",
        "aliases": ["Moby Dick"],
        "author": "Herman Melville",
        "publication_year": "1851",
        "form": ["novel"],
        "genre": ["adventure fiction"],
        "characters": ["Ishmael", "Captain Ahab", "Moby Dick"],
        "themes": ["obsession", "fate", "knowledge"],
    },
    {
        "work": "The Scarlet Letter",
        "aliases": [],
        "author": "Nathaniel Hawthorne",
        "publication_year": "1850",
        "form": ["novel"],
        "genre": ["historical novel"],
        "characters": ["Hester Prynne", "Arthur Dimmesdale", "Pearl"],
        "themes": ["sin", "public shame", "identity"],
    },
    {
        "work": "The Adventures of Huckleberry Finn",
        "aliases": ["Adventures of Huckleberry Finn", "Huckleberry Finn"],
        "author": "Mark Twain",
        "publication_year": "1884",
        "form": ["novel"],
        "genre": ["picaresque novel"],
        "characters": ["Huckleberry Finn", "Jim"],
        "themes": ["freedom", "race", "moral conscience"],
    },
    {
        "work": "The Great Gatsby",
        "aliases": ["Great Gatsby"],
        "author": "F. Scott Fitzgerald",
        "publication_year": "1925",
        "form": ["novel"],
        "genre": ["modernist fiction"],
        "characters": ["Jay Gatsby", "Nick Carraway", "Daisy Buchanan"],
        "themes": ["wealth", "class", "American dream"],
    },
    {
        "work": "To the Lighthouse",
        "aliases": [],
        "author": "Virginia Woolf",
        "publication_year": "1927",
        "form": ["novel"],
        "genre": ["modernist fiction"],
        "characters": ["Mrs Ramsay", "Mr Ramsay", "Lily Briscoe"],
        "themes": ["time", "perception", "family"],
    },
    {
        "work": "Mrs Dalloway",
        "aliases": [],
        "author": "Virginia Woolf",
        "publication_year": "1925",
        "form": ["novel"],
        "genre": ["modernist fiction"],
        "characters": ["Clarissa Dalloway", "Septimus Warren Smith"],
        "themes": ["consciousness", "memory", "war trauma"],
    },
    {
        "work": "Heart of Darkness",
        "aliases": [],
        "author": "Joseph Conrad",
        "publication_year": "1899",
        "form": ["novella"],
        "genre": ["modernist fiction"],
        "characters": ["Marlow", "Kurtz"],
        "themes": ["colonialism", "violence", "moral ambiguity"],
    },
    {
        "work": "The Turn of the Screw",
        "aliases": ["Turn of the Screw"],
        "author": "Henry James",
        "publication_year": "1898",
        "form": ["novella"],
        "genre": ["Gothic fiction"],
        "characters": ["the governess", "Miles", "Flora"],
        "themes": ["ambiguity", "perception", "innocence"],
    },
    {
        "work": "The Awakening",
        "aliases": [],
        "author": "Kate Chopin",
        "publication_year": "1899",
        "form": ["novel"],
        "genre": ["realist fiction"],
        "characters": ["Edna Pontellier", "Leonce Pontellier", "Robert Lebrun"],
        "themes": ["independence", "gender", "desire"],
    },
    {
        "work": "The Yellow Wallpaper",
        "aliases": ["Yellow Wallpaper"],
        "author": "Charlotte Perkins Gilman",
        "publication_year": "1892",
        "form": ["short story"],
        "genre": ["Gothic fiction"],
        "characters": ["the narrator", "John"],
        "themes": ["mental health", "gender", "confinement"],
    },
    {
        "work": "Middlemarch",
        "aliases": [],
        "author": "George Eliot",
        "publication_year": "1871",
        "form": ["novel"],
        "genre": ["realist fiction"],
        "characters": ["Dorothea Brooke", "Tertius Lydgate", "Will Ladislaw"],
        "themes": ["marriage", "reform", "provincial life"],
    },
    {
        "work": "Tess of the d'Urbervilles",
        "aliases": ["Tess of the dUrbervilles"],
        "author": "Thomas Hardy",
        "publication_year": "1891",
        "form": ["novel"],
        "genre": ["tragedy", "realist fiction"],
        "characters": ["Tess Durbeyfield", "Alec d'Urberville", "Angel Clare"],
        "themes": ["fate", "social judgment", "sexual double standards"],
    },
    {
        "work": "The Mayor of Casterbridge",
        "aliases": ["Mayor of Casterbridge"],
        "author": "Thomas Hardy",
        "publication_year": "1886",
        "form": ["novel"],
        "genre": ["realist fiction"],
        "characters": ["Michael Henchard", "Elizabeth-Jane Newson", "Donald Farfrae"],
        "themes": ["character", "fate", "social reputation"],
    },
    {
        "work": "The Importance of Being Earnest",
        "aliases": ["Importance of Being Earnest"],
        "author": "Oscar Wilde",
        "publication_year": "1895",
        "form": ["play"],
        "genre": ["comedy", "farce"],
        "characters": ["Jack Worthing", "Algernon Moncrieff", "Gwendolen Fairfax", "Cecily Cardew"],
        "themes": ["identity", "marriage", "social performance"],
    },
    {
        "work": "A Doll's House",
        "aliases": ["Doll's House"],
        "author": "Henrik Ibsen",
        "publication_year": "1879",
        "form": ["play"],
        "genre": ["realist drama"],
        "characters": ["Nora Helmer", "Torvald Helmer", "Krogstad", "Mrs Linde"],
        "themes": ["marriage", "gender", "selfhood"],
    },
    {
        "work": "The Odyssey",
        "aliases": ["Odyssey"],
        "author": "Homer",
        "publication_year": "8th century BCE",
        "form": ["epic poem"],
        "genre": ["epic poetry"],
        "characters": ["Odysseus", "Penelope", "Telemachus"],
        "themes": ["homecoming", "identity", "hospitality"],
    },
]


def _as_list(values: object) -> List[str]:
    if isinstance(values, list):
        return [str(value).strip() for value in values if str(value).strip()]
    value = str(values or "").strip()
    return [value] if value else []


def _row(work: str, relation: str, value: str, evidence: str) -> Dict[str, str]:
    return {
        "entity": work,
        "relation": relation,
        "value": value,
        "work": work,
        "evidence": evidence,
        "source": SOURCE,
    }


def build_rows(seed_works: Iterable[Dict[str, object]]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for item in seed_works:
        work = str(item["work"])
        author = str(item["author"])
        year = str(item["publication_year"])
        rows.append(_row(work, "author", author, f"{work} is attributed to {author}."))
        rows.append(_row(work, "publication_year", year, f"{work} is conventionally dated to {year}."))
        for alias in _as_list(item.get("aliases")):
            rows.append(_row(work, "alias", alias, f"{alias} is an alternate reference for {work}."))
        for form in _as_list(item.get("form")):
            rows.append(_row(work, "form", form, f"{work} is a {form}."))
        for genre in _as_list(item.get("genre")):
            rows.append(_row(work, "genre", genre, f"{work} is commonly described as {genre}."))
        for character in _as_list(item.get("characters")):
            rows.append(_row(work, "central_character", character, f"{character} is a central character in {work}."))
        for theme in _as_list(item.get("themes")):
            rows.append(_row(work, "theme", theme, f"{work} is often discussed through the theme of {theme}."))
    return rows


def write_rows(rows: List[Dict[str, str]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    columns = ["entity", "relation", "value", "work", "evidence", "source"]
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the ConsensusScope curated ESL literary knowledge graph.")
    parser.add_argument("--output", default=str(ROOT / "data" / "knowledge" / "literary_kg_triples.csv"))
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    seed = CURATED_WORKS[: args.limit] if args.limit else CURATED_WORKS
    rows = build_rows(seed)
    write_rows(rows, Path(args.output))
    print(f"Wrote {len(rows)} triples to {args.output}")
