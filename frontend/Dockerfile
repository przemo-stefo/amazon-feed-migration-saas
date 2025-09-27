# Build stage
FROM node:18-alpine as build

WORKDIR /app

# Kopiowanie package.json i package-lock.json
COPY package*.json ./

# Instalacja zależności
RUN npm ci --only=production

# Kopiowanie kodu źródłowego
COPY . .

# Argumenty build
ARG REACT_APP_API_URL=http://localhost:8000
ENV REACT_APP_API_URL=$REACT_APP_API_URL

# Build aplikacji
RUN npm run build

# Production stage
FROM nginx:alpine

# Kopiowanie built aplikacji do nginx
COPY --from=build /app/build /usr/share/nginx/html

# Kopiowanie konfiguracji nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 3000

# Start nginx
CMD ["nginx", "-g", "daemon off;"]