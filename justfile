# Show available commands.
default:
    @just --list

# Export Han-Lo and romanized entries, including alternate readings.
export:
    python3 tools/lexicon.py build-csv

# Export all entries, including pure Hanji and alternate readings.
export-all:
    python3 tools/lexicon.py build-csv --include-pure-hanji

# Export Han-Lo and romanized entries with canonical readings only.
export-canonical:
    python3 tools/lexicon.py build-csv --canonical-only

# Export all entries with canonical readings only.
export-all-canonical:
    python3 tools/lexicon.py build-csv --include-pure-hanji --canonical-only

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
