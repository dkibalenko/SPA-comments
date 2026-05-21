FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM alpine:3.19
COPY --from=builder /app/dist /dist
# one-shot copy command - isn't a server
CMD ["sh", "-c", "cp -r /dist/. /app/frontend/"]
