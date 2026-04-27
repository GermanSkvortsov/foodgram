FROM node:18-alpine as build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . ./
RUN npm run build

FROM alpine:latest

WORKDIR /work

COPY --from=build /app/build /work/build

CMD cp -r /work/build/* /build-volume/ && tail -f /dev/null
