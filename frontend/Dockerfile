FROM node:18-alpine as build
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --silent

COPY . .
RUN npm run build

FROM node:18-alpine
WORKDIR /app
COPY --from=build /app/dist ./dist

EXPOSE 5173
CMD ["npx", "vite", "preview", "--host", "0.0.0.0", "--port", "5173"]
