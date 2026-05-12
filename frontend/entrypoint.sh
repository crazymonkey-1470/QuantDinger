#!/bin/sh
# QuantDinger frontend entrypoint.
#
# Renders nginx.conf.template with BACKEND_URL + PORT and then hands off to
# the official nginx entrypoint chain. We do our own envsubst (against an
# explicit shell-format) instead of relying on the image's built-in
# /docker-entrypoint.d/20-envsubst-on-templates.sh, whose env-var filter is
# regex-based and has tripped us up.
set -eu

# Strip surrounding whitespace and angle brackets — common when the value
# is pasted from markdown auto-links or plain-text emails (RFC 3986 §3.2.2).
if [ -n "${BACKEND_URL:-}" ]; then
    BACKEND_URL=$(printf '%s' "$BACKEND_URL" | sed 's/^[[:space:]<]*//; s/[[:space:]>]*$//')
fi

# Normalize BACKEND_URL: if user gave a bare host (e.g. Railway public domain
# without scheme), default it to https://. Public Railway domains are HTTPS.
if [ -n "${BACKEND_URL:-}" ]; then
    case "$BACKEND_URL" in
        http://*|https://*) ;;
        *) BACKEND_URL="https://$BACKEND_URL" ;;
    esac
fi

: "${BACKEND_URL:=http://backend:5000}"
: "${PORT:=80}"
export BACKEND_URL PORT

echo "[frontend-entrypoint] PORT=$PORT BACKEND_URL=$BACKEND_URL"

# Explicit shell-format: only ${BACKEND_URL} and ${PORT} get substituted.
# nginx's own $host, $remote_addr, $proxy_add_x_forwarded_for, etc. stay
# literal because they aren't named here.
envsubst '${BACKEND_URL} ${PORT}' \
    < /templates/default.conf.template \
    > /etc/nginx/conf.d/default.conf

exec /docker-entrypoint.sh "$@"
