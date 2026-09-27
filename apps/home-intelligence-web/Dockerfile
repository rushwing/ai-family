FROM node:22-bookworm-slim AS build
WORKDIR /app

COPY package.json package-lock.json .npmrc ./
RUN npm ci --include=dev --include=optional --no-audit --no-fund

COPY . .
RUN npm run build

FROM node:22-bookworm-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production

COPY --from=build /app /app
EXPOSE 3000
CMD ["npm", "run", "start:lan-demo"]
