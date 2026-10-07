#!/usr/bin/env bash
set -e

echo "============================================================"
echo "         Building CoCompute Linux Standalone Worker         "
echo "============================================================"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

DIST_DIR="$REPO_ROOT/dist/linux"
mkdir -p "$DIST_DIR"

if command -v pyinstaller >/dev/null 2>&1; then
    echo "Packaging with PyInstaller on Linux x64..."
    pyinstaller --clean \
        --onefile \
        --distpath "$DIST_DIR" \
        --name cocompute-worker \
        --add-data "shared:shared" \
        --add-data "worker/app:worker/app" \
        --hidden-import "psutil" \
        --hidden-import "websockets" \
        --hidden-import "httpx" \
        --exclude-module "torch" \
        --exclude-module "tensorflow" \
        --exclude-module "PySide6" \
        worker/start_worker.py

    echo "[SUCCESS] Standalone Linux worker binary created at $DIST_DIR/cocompute-worker"
else
    echo "PyInstaller not found. Creating portable shell launcher package..."
    cat << 'EOF' > "$DIST_DIR/cocompute-worker"
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
python3 -m worker.app.main "$@"
EOF
    chmod +x "$DIST_DIR/cocompute-worker"
    echo "[INFO] Created portable launcher at $DIST_DIR/cocompute-worker"
fi
