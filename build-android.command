#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

export VIRTUAL_ENV="$PROJECT_DIR/.build-venv"
export JAVA_HOME="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
export PATH="$PROJECT_DIR/.build-tools:$VIRTUAL_ENV/bin:$JAVA_HOME/bin:/opt/homebrew/opt/autoconf/bin:/opt/homebrew/opt/automake/bin:/opt/homebrew/opt/libtool/bin:/opt/homebrew/opt/pkgconf/bin:/opt/homebrew/opt/cmake/bin:/opt/homebrew/opt/ninja/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export CPPFLAGS="-I/opt/homebrew/opt/zlib/include"
export LDFLAGS="-L/opt/homebrew/opt/zlib/lib"
export PKG_CONFIG_PATH="/opt/homebrew/opt/zlib/lib/pkgconfig"

exec "$VIRTUAL_ENV/bin/buildozer" -v android debug
