#!/bin/bash
# UPDATE_MAC.command — descarga el código nuevo sin borrar tus vídeos y ajustes

cd "$(dirname "$0")/.."
APP_DIR="$(pwd)"

echo ""
echo "=================================================="
echo "  🎂 La Merced — Actualizando..."
echo "=================================================="
echo ""

# 1. Back up data folder
if [ -d "$APP_DIR/data" ]; then
  cp -r "$APP_DIR/data" /tmp/lamerced_data_backup
  echo "✓ Datos guardados (vídeos, ajustes)"
fi

# 2. Download new zip
echo "↓ Descargando última versión..."
curl -sL "https://github.com/jorgedani16/claude/archive/refs/heads/claude/nice-wright-9oUnU.zip" -o /tmp/lamerced_update.zip

# 3. Extract to temp folder
rm -rf /tmp/lamerced_extract
unzip -q /tmp/lamerced_update.zip -d /tmp/lamerced_extract

# 4. Copy code files only (not data/)
EXTRACTED="/tmp/lamerced_extract/CLAUDE-claude-nice-wright-9oUnU/content_team"
cp -r "$EXTRACTED/agents"      "$APP_DIR/"
cp -r "$EXTRACTED/integrations" "$APP_DIR/"
cp -r "$EXTRACTED/templates"   "$APP_DIR/"
cp -r "$EXTRACTED/static"      "$APP_DIR/"
cp    "$EXTRACTED/app.py"      "$APP_DIR/"
cp    "$EXTRACTED/config.py"   "$APP_DIR/"
cp    "$EXTRACTED/pipeline.py" "$APP_DIR/"
cp    "$EXTRACTED/requirements.txt" "$APP_DIR/"
echo "✓ Código actualizado"

# 5. Restore data
if [ -d /tmp/lamerced_data_backup ]; then
  cp -r /tmp/lamerced_data_backup/. "$APP_DIR/data/"
  echo "✓ Vídeos y ajustes restaurados"
fi

# 6. Install any new dependencies
pip3 install -q -r "$APP_DIR/requirements.txt"

# 7. Clean up
rm -rf /tmp/lamerced_update.zip /tmp/lamerced_extract /tmp/lamerced_data_backup

echo ""
echo "✓ Actualización completada. Reinicia la app:"
echo "  python3 app.py"
echo ""
read -p "Pulsa Enter para cerrar"
