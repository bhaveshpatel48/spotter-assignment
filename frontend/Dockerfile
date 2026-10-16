# Local Docker runs only; Render serves the frontend as a static site (ADR-0015).
FROM node:24-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Vite inlines VITE_ variables into the bundle, so they are needed at build time.
ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_TOMTOM_MAP_KEY
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_TOMTOM_MAP_KEY=$VITE_TOMTOM_MAP_KEY

RUN npm run build

FROM nginx:1.28-alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
