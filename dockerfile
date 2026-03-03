FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY *.go ./
RUN go build -o tz-sig main.go
FROM alpine:latest
WORKDIR /app
COPY --from=builder /app/tz-sig .
COPY bg.jpg font.ttf ./
EXPOSE 10000
CMD ["./tz-sig"]
