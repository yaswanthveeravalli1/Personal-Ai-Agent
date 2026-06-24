"""
Import .md memory files from Claude's memory directory into Jarvis's SQLite database.
Parses markdown into individual facts, generates embeddings, and stores them.

Usage:
    python import_memory.py <your_telegram_user_id>

Example:
    python import_memory.py 123456789
"""

import os
import re
import sys
from pathlib import Path

# Add current directory to path for local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db, add_entry
from embeddings import embed

MEMORY_DIR = r"C:\Users\yaswa\.claude\memory"

# Map subfolder names to memory sections
FOLDER_TO_SECTION = {
    "profile": "Facts",
    "diary": "Diary",
    "relationships": "Relationships",
    "finances": "Finances",
    "system": "Preferences",
}


def parse_md_to_entries(filepath):
    """Parse a markdown file into individual memory entries.
    Each meaningful line becomes a separate entry for better semantic search."""
    entries = []
    current_heading = ""

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()

        # Skip empty lines, horizontal rules, timestamps, code blocks, structure diagrams
        if not line or line.startswith("---") or line.startswith("*Last updated") or line.startswith("```"):
            continue
        if line.startswith("├") or line.startswith("│") or line.startswith("└"):
            continue

        # Track headings for context
        if line.startswith("#"):
            current_heading = re.sub(r"^#+\s*", "", line).strip()
            # Remove emoji from heading
            current_heading = re.sub(r"[^\w\s&,()-]", "", current_heading).strip()
            continue

        # Skip table separators
        if re.match(r"^\|[-\s|]+\|$", line):
            continue

        # Parse table rows
        if line.startswith("|"):
            cells = [c.strip().strip("*").strip() for c in line.split("|") if c.strip()]
            if len(cells) >= 2:
                entry = " — ".join(cells)
                if current_heading:
                    entry = f"[{current_heading}] {entry}"
                entries.append(entry)
            continue

        # Parse bullet points
        if line.startswith("- "):
            entry = line[2:].strip()
            # Remove bold markers
            entry = entry.replace("**", "")
            if current_heading:
                entry = f"[{current_heading}] {entry}"
            entries.append(entry)
            continue

        # Indented sub-bullets
        if line.startswith("  - "):
            entry = line[4:].strip()
            entry = entry.replace("**", "")
            if current_heading:
                entry = f"[{current_heading}] {entry}"
            entries.append(entry)
            continue

        # Any other non-empty content line
        clean = line.replace("**", "").strip()
        if len(clean) > 5:  # Skip very short fragments
            if current_heading:
                clean = f"[{current_heading}] {clean}"
            entries.append(clean)

    return entries


def import_memories(user_id):
    """Scan all .md files in the memory directory and import them."""
    init_db()

    memory_path = Path(MEMORY_DIR)
    if not memory_path.exists():
        print(f"[ERROR] Memory directory not found: {MEMORY_DIR}")
        return

    total_imported = 0
    total_skipped = 0
    total_files = 0

    # Walk through all .md files
    for md_file in sorted(memory_path.rglob("*.md")):
        # Skip the index file itself
        if md_file.name == "MEMORY.md":
            continue

        # Determine section from parent folder
        relative = md_file.relative_to(memory_path)
        folder = relative.parts[0] if len(relative.parts) > 1 else "general"
        section = FOLDER_TO_SECTION.get(folder, "Facts")

        # Add source file context to section
        file_label = md_file.stem.replace("_", " ").title()
        full_section = f"{section}/{file_label}"

        print(f"\n[FILE] Processing: {relative}")
        entries = parse_md_to_entries(str(md_file))
        print(f"   Found {len(entries)} entries")

        imported = 0
        skipped = 0
        for entry in entries:
            try:
                embedding = embed(entry)
                added = add_entry(user_id, full_section, entry, embedding)
                if added:
                    imported += 1
                else:
                    skipped += 1
            except Exception as e:
                print(f"   [WARN] Error embedding entry: {e}")
                skipped += 1

        print(f"   [OK] Imported: {imported}, Skipped (duplicates): {skipped}")
        total_imported += imported
        total_skipped += skipped
        total_files += 1

    print(f"\n{'='*50}")
    print(f"[DONE] Import complete!")
    print(f"   Files processed: {total_files}")
    print(f"   Total entries imported: {total_imported}")
    print(f"   Total duplicates skipped: {total_skipped}")
    print(f"   User ID: {user_id}")
    print(f"{'='*50}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_memory.py <your_telegram_user_id>")
        print("\nTo find your Telegram user ID:")
        print("  1. Message @userinfobot on Telegram")
        print("  2. It will reply with your numeric user ID")
        sys.exit(1)

    user_id = sys.argv[1]
    print(f"[IMPORT] Importing Claude memories for Telegram user: {user_id}")
    print(f"[SOURCE] {MEMORY_DIR}")
    import_memories(user_id)

