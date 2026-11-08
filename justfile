# Show available commands.
default:
    @just --list

# Export Han-Lo and romanized entries, including alternate readings.
export:
    python3 tools/lexicon.py build-csv

# Export Han-Lo and romanized entries with canonical readings and contractions.
export-canonical-contractions:
    python3 tools/lexicon.py build-csv --canonical-and-contractions

# Export every CSV variant.
export-all: export export-canonical-contractions

# Validate entries, IDs, formatting, and source references.
validate:
    python3 tools/lexicon.py validate

# Check canonical formatting without changing files.
format-check:
    python3 tools/lexicon.py format --check

# Apply canonical entry formatting and paths.
format:
    python3 tools/lexicon.py format

# Run the maintenance tool test suite.
test:
    python3 -m unittest discover -s tests -v

# Run all read-only checks.
check: validate format-check test
