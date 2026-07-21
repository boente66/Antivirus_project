#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$PROJECT_ROOT/.venv/bin/python}"
PACKAGE_NAME="antivirus-project-test"
APP_VERSION="$(cd "$PROJECT_ROOT" && "$PYTHON_BIN" -c 'from utils.app_metadata import APP_VERSION; print(APP_VERSION)' 2>/dev/null || true)"
DEFAULT_DEB_VERSION="${APP_VERSION/-test/~test}-1"
DEB_VERSION="${PACKAGE_VERSION:-$DEFAULT_DEB_VERSION}"
DEB_ARCH="${DEB_ARCH:-$(dpkg --print-architecture)}"
OUTPUT_DIR="${OUTPUT_DIR:-$PROJECT_ROOT/dist/deb}"
BUILD_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/antivirus-project-deb.XXXXXX")"

cleanup() {
    rm -rf -- "$BUILD_ROOT"
}
trap cleanup EXIT

fail() {
    printf 'ERRO: %s\n' "$1" >&2
    exit 1
}

[[ -x "$PYTHON_BIN" ]] || fail "Python do projeto não encontrado: $PYTHON_BIN"
command -v dpkg >/dev/null || fail "dpkg não está instalado"
command -v dpkg-deb >/dev/null || fail "dpkg-deb não está instalado"
command -v desktop-file-validate >/dev/null || \
    fail "desktop-file-validate não está instalado (pacote desktop-file-utils)"
[[ "$DEB_VERSION" =~ ^[0-9A-Za-z.+:~_-]+$ ]] || fail "Versão Debian inválida"
[[ "$DEB_ARCH" =~ ^[0-9A-Za-z-]+$ ]] || fail "Arquitetura Debian inválida"
[[ -n "$APP_VERSION" ]] || fail "Versão da aplicação não encontrada"

PYINSTALLER_DIST="$BUILD_ROOT/pyinstaller-dist"
PYINSTALLER_WORK="$BUILD_ROOT/pyinstaller-work"
PYINSTALLER_SPEC="$BUILD_ROOT/pyinstaller-spec"
PACKAGE_ROOT="$BUILD_ROOT/package-root"
OUTPUT_FILE="$OUTPUT_DIR/${PACKAGE_NAME}_${DEB_VERSION}_${DEB_ARCH}.deb"

printf 'Construindo binário PyInstaller %s para %s...\n' "$APP_VERSION" "$DEB_ARCH"
cd "$PROJECT_ROOT"
"$PYTHON_BIN" -m PyInstaller \
    --noconfirm \
    --clean \
    --windowed \
    --noupx \
    --name antivirus-project \
    --paths "$PROJECT_ROOT" \
    --add-data "$PROJECT_ROOT/resources:resources" \
    --distpath "$PYINSTALLER_DIST" \
    --workpath "$PYINSTALLER_WORK" \
    --specpath "$PYINSTALLER_SPEC" \
    "$PROJECT_ROOT/main.py"

BUNDLE_DIR="$PYINSTALLER_DIST/antivirus-project"
[[ -x "$BUNDLE_DIR/antivirus-project" ]] || fail "Binário PyInstaller não foi criado"

printf 'Executando diagnóstico do binário empacotado...\n'
"$BUNDLE_DIR/antivirus-project" --version
"$BUNDLE_DIR/antivirus-project" --diagnose

install -d \
    "$PACKAGE_ROOT/DEBIAN" \
    "$PACKAGE_ROOT/opt/antivirus-project" \
    "$PACKAGE_ROOT/usr/bin" \
    "$PACKAGE_ROOT/usr/share/applications" \
    "$PACKAGE_ROOT/usr/share/icons/hicolor/scalable/apps" \
    "$PACKAGE_ROOT/usr/share/doc/$PACKAGE_NAME"

cp -a "$BUNDLE_DIR/." "$PACKAGE_ROOT/opt/antivirus-project/"
install -m 0755 "$SCRIPT_DIR/antivirus-project" "$PACKAGE_ROOT/usr/bin/antivirus-project"
install -m 0644 "$SCRIPT_DIR/antivirus-project.desktop" \
    "$PACKAGE_ROOT/usr/share/applications/antivirus-project.desktop"
install -m 0644 "$PROJECT_ROOT/resources/icons/shield.svg" \
    "$PACKAGE_ROOT/usr/share/icons/hicolor/scalable/apps/antivirus-project.svg"
install -m 0644 "$PROJECT_ROOT/LICENSE" \
    "$PACKAGE_ROOT/usr/share/doc/$PACKAGE_NAME/copyright"
install -m 0644 "$PROJECT_ROOT/README.md" \
    "$PACKAGE_ROOT/usr/share/doc/$PACKAGE_NAME/README.md"
install -m 0644 "$PROJECT_ROOT/NOTICE-BR.md" \
    "$PACKAGE_ROOT/usr/share/doc/$PACKAGE_NAME/NOTICE-BR.md"
install -m 0644 "$SCRIPT_DIR/README.md" \
    "$PACKAGE_ROOT/usr/share/doc/$PACKAGE_NAME/README.Debian.md"

INSTALLED_SIZE="$(du -sk "$PACKAGE_ROOT" | awk '{print $1}')"
cat >"$PACKAGE_ROOT/DEBIAN/control" <<EOF
Package: $PACKAGE_NAME
Version: $DEB_VERSION
Section: utils
Priority: optional
Architecture: $DEB_ARCH
Maintainer: Leonardo Boente <boente66@users.noreply.github.com>
Installed-Size: $INSTALLED_SIZE
Depends: libc6, libglib2.0-0, libgl1, libx11-6, libxcb1, libxkbcommon-x11-0, libxcb-xinerama0, policykit-1, clamav, clamav-daemon, clamav-freshclam, ufw
Homepage: https://github.com/boente66/Antivirus_project
Description: antivírus com interface gráfica - pacote para testes
 Pacote de avaliação para Linux contendo interface PyQt5, integração
 obrigatória com o daemon ClamAV e operações UFW autorizadas
 individualmente por Polkit. O scan requer assinaturas atualizadas.
 Não deve ser tratado como uma distribuição de produção.
EOF

mkdir -p "$OUTPUT_DIR"
chmod -R go-w "$PACKAGE_ROOT"
dpkg-deb --build --root-owner-group "$PACKAGE_ROOT" "$OUTPUT_FILE"

printf 'Validando metadados e conteúdo do pacote...\n'
dpkg-deb --info "$OUTPUT_FILE" >/dev/null
dpkg-deb --contents "$OUTPUT_FILE" >/dev/null
desktop-file-validate "$PACKAGE_ROOT/usr/share/applications/antivirus-project.desktop"

EXTRACT_ROOT="$BUILD_ROOT/extracted"
mkdir -p "$EXTRACT_ROOT"
dpkg-deb --extract "$OUTPUT_FILE" "$EXTRACT_ROOT"
"$EXTRACT_ROOT/opt/antivirus-project/antivirus-project" --version
"$EXTRACT_ROOT/opt/antivirus-project/antivirus-project" --diagnose

if command -v lintian >/dev/null; then
    printf 'Executando lintian...\n'
    lintian "$OUTPUT_FILE"
else
    printf 'Aviso: lintian não instalado; validação complementar ignorada.\n'
fi

printf '\nPacote criado com sucesso:\n%s\n' "$OUTPUT_FILE"
