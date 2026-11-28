# syntax=docker/dockerfile:1.7

# -----------------------------------------------------------------------------
# deps: install dependencies from the lockfile, cached separately from the sources
# -----------------------------------------------------------------------------
FROM node:26-alpine@sha256:e88a35be04478413b7c71c455cd9865de9b9360e1f43456be5951032d7ac1a66 AS deps
WORKDIR /app
# Copy .npmrc (engine-strict) too: npm ci checks the base node/npm against engines in package.json,
# so a build on the "wrong" base fails at once instead of silently drifting the lockfile.
COPY package.json package-lock.json .npmrc ./
RUN npm ci

# -----------------------------------------------------------------------------
# dev: used by docker-compose (target: dev). Sources are volume-mounted at runtime; CMD syncs
# node_modules at start and runs the Vite dev server.
# -----------------------------------------------------------------------------
FROM deps AS dev
COPY . .
EXPOSE 5173
# `npm install` at start syncs the node_modules named volume with package.json/lock (the volume
# survives a rebuild and would otherwise go stale when dependencies change).
CMD ["sh", "-c", "npm install && npm run dev -- --host 0.0.0.0"]

# -----------------------------------------------------------------------------
# build: production bundle (tsc -b && vite build) -> /app/dist
# -----------------------------------------------------------------------------
FROM deps AS build
COPY . .
RUN npm run build

# -----------------------------------------------------------------------------
# final: nginx serves static files. Proxying /v1 to the backend is done by the external Caddy;
# nginx here is only a static SPA server.
# -----------------------------------------------------------------------------
# nginx-unprivileged: master and workers run non-root (uid 101) and listen on :8080 (a port >1024,
# no root needed). Proxying /v1 is done by the external Caddy (reverse_proxy frontend:8080).
FROM nginxinc/nginx-unprivileged:alpine@sha256:b5047b9b76845eac124358373c6852377c52e4b05834a47647e955dd91cb8f1e AS final
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
