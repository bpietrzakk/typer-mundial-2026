# multi-stage: build the React app with node, then serve static files via nginx

# --- build stage ---
FROM node:22-alpine AS build
WORKDIR /app

# install deps from lockfile (cached unless package files change)
COPY package.json package-lock.json ./
RUN npm ci

# VITE_API_URL is baked into the bundle at build time. in the dockerised
# setup the API lives behind nginx at /api (see nginx.conf), so axios calls
# /api/auth/login etc. in local `npm run dev` this is unset -> '' -> vite
# proxy handles it. axios.js already reads import.meta.env.VITE_API_URL.
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL

COPY . .
RUN npm run build

# --- serve stage ---
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
