# QuantDinger Frontend
# Build context: ./frontend (see docker-compose.yml)
#
# Serves the pre-built SPA from `dist/` (nginx). Vue source lives in a
# separate private repository: build there, then copy `dist/` into this tree.

ARG RUNTIME_IMAGE=nginx:1.25-alpine

FROM ${RUNTIME_IMAGE}

RUN apk add --no-cache curl

# Defaults; overridden at runtime by docker-compose / Railway env vars.
# entrypoint.sh prepends https:// if BACKEND_URL is given as a bare host.
ENV BACKEND_URL=http://backend:5000 \
    PORT=80

# Template lives outside /etc/nginx/templates/ so the image's built-in
# 20-envsubst-on-templates.sh leaves it alone — entrypoint.sh renders it.
COPY nginx.conf.template /templates/default.conf.template
COPY dist/ /usr/share/nginx/html/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
