# QuantDinger Frontend
# Build context: ./frontend (see docker-compose.yml)
#
# Serves the pre-built SPA from `dist/` (nginx). Vue source lives in a
# separate private repository: build there, then copy `dist/` into this tree.

ARG RUNTIME_IMAGE=nginx:1.25-alpine

FROM ${RUNTIME_IMAGE}

RUN apk add --no-cache curl

# nginx:alpine auto-runs envsubst on /etc/nginx/templates/*.template at start.
# Pin the filter so only ${BACKEND_URL} is substituted — without it, nginx's
# own $-variables ($host, $remote_addr, ...) would also get clobbered.
ENV NGINX_ENVSUBST_FILTER=BACKEND_URL \
    BACKEND_URL=http://backend:5000

COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY dist/ /usr/share/nginx/html/

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
