#!/bin/sh
# Build dist/TMate-1.0-Windows.zip from this checkout.
#
# - top-level folder TMate-1.0-Windows\ inside the ZIP;
# - Windows scripts and text files converted to CRLF;
# - __pycache__, intermediate manual passes, udev rules, tools/ and dist/ left out;
# - unit tests are run first and must pass.
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
NAME=TMate-1.0-Windows
DIST="$ROOT/dist"
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT

cd "$ROOT"
python3 -m unittest discover -s tests -q

# Rebuild the PDF manual from docs/windows.md when reportlab is available.
if python3 -c "import reportlab" 2>/dev/null; then
    python3 tools/build_windows_manual.py
else
    echo "warning: reportlab missing; shipping the existing manual PDF" >&2
fi

# Windows PowerShell 5.1 reads BOM-less scripts as ANSI: keep them ASCII.
if LC_ALL=C grep -nP '[^\x00-\x7F]' setup-windows.ps1 setup-windows.cmd \
        bin/*.cmd bin/*.vbs WINDOWS-QUICKSTART.txt; then
    echo "error: non-ASCII characters in Windows scripts (see above)" >&2
    exit 1
fi

PKG="$STAGE/$NAME"
mkdir -p "$PKG"
for item in README.md WINDOWS-QUICKSTART.txt TMate-1.0-Windows-Manual.pdf \
            requirements.txt requirements-midi.txt \
            setup-windows.ps1 setup-windows.cmd \
            bin docs tests tmate1 tmate1_midi windows; do
    cp -R "$item" "$PKG/"
done
find "$PKG" -name __pycache__ -type d -prune -exec rm -rf {} +
find "$PKG" -name '*.pyc' -delete

# CRLF for files Windows tools open directly.
find "$PKG" -type f \( -name '*.cmd' -o -name '*.ps1' -o -name '*.vbs' \
        -o -name '*.txt' \) | while read -r f; do
    sed -i 's/\r$//; s/$/\r/' "$f"
done

mkdir -p "$DIST"
rm -f "$DIST/$NAME.zip"
(cd "$STAGE" && zip -qr -X "$DIST/$NAME.zip" "$NAME")
(cd "$DIST" && sha256sum "$NAME.zip" > "$NAME.zip.sha256")
echo "built $DIST/$NAME.zip"
cat "$DIST/$NAME.zip.sha256"
