FROM node:18-alpine as build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . ./
RUN npm run build

FROM alpine:latest

COPY --from=build /app/build /build

CMD cp -r /build/* /frontend-output/ && echo "✅ Frontend build copied" && exit 0
