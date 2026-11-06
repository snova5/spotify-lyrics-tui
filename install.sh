#!/usr/bin/env bash
set -e

NAME="spotifylyr"
SHARE="$HOME/.local/share/$NAME"
BIN="$HOME/.local/bin"
HERE="$(cd "$(dirname "$0")" && pwd)"

if [ "$1" = "--uninstall" ]; then
  rm -f "$BIN/$NAME"
  rm -rf "$SHARE"
  echo "$NAME was removed."
  exit 0
fi

if [ ! -f "$HERE/spotify_lyrics.py" ]; then
  echo "spotify_lyrics.py not found next to install.sh"
  exit 1
fi

mkdir -p "$SHARE" "$BIN"
cp "$HERE/spotify_lyrics.py" "$SHARE/spotify_lyrics.py"

cat > "$BIN/$NAME" <<EOF
#!/usr/bin/env bash
exec python3 "$SHARE/spotify_lyrics.py" "\$@"
EOF
chmod +x "$BIN/$NAME"

echo "Installed: $BIN/$NAME"

for dep in playerctl cava; do
  if ! command -v "$dep" >/dev/null 2>&1; then
    echo "Note: $dep is not installed (sudo dnf install $dep)"
  fi
done

case ":$PATH:" in
  *":$BIN:"*)
    echo "Run it with: $NAME"
    ;;
  *)
    echo "$BIN is not in your PATH yet. Add it with:"
    echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc && source ~/.bashrc"
    echo "Then run: $NAME"
    ;;
esac
