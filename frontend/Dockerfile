FROM node:18-alpine AS build

WORKDIR /app

ARG VITE_API_URL=http://136.234.4.160:8000
ARG VITE_WS_URL=ws://136.234.4.160:8000
ARG VITE_S3_PUBLIC_URL=http://136.234.4.160:9100
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_WS_URL=$VITE_WS_URL
ENV VITE_S3_PUBLIC_URL=$VITE_S3_PUBLIC_URL

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
