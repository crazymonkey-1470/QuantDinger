# QuantDinger Frontend
# Build context: repository root (see docker-compose.yml)
#
# Serves the pre-built SPA from `frontend/dist/` (nginx). Vue source lives in a
# separate private repository: build there, then copy `dist/` into this tree.

ARG RUNTIME_IMAGE=nginx:1.25-alpine

FROM ${RUNTIME_IMAGE}

RUN apk add --no-cache curl

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY frontend/dist/ /usr/share/nginx/html/

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
