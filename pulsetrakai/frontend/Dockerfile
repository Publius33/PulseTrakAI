# Minimal frontend Dockerfile for static site
FROM node:18-alpine as build
WORKDIR /app
COPY . .
RUN npm ci && npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

# © PUBLIUS33™ — PulseTrakAI™. All Rights Reserved.
