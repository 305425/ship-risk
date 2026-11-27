FROM node:22-alpine AS build
WORKDIR /web
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY docker/15-mlflow-auth.envsh /docker-entrypoint.d/15-mlflow-auth.envsh
RUN chmod 755 /docker-entrypoint.d/15-mlflow-auth.envsh
COPY --from=build /web/dist /usr/share/nginx/html
