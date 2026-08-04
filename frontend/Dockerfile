# Etapa 1: Construcción
FROM node:20-alpine as build

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos y carpetas necesarias
COPY package*.json ./
COPY . .

# Instala dependencias y compila el proyecto
RUN npm install && npm run build

# Etapa 2: Servir con Nginx
FROM nginx:alpine

# Copia los archivos construidos desde la etapa anterior al directorio de Nginx
COPY --from=build /app/dist /usr/share/nginx/html

# Copia una configuración mínima de Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expone el puerto 80
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]