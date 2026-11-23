FROM python:3.14-slim@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f AS generator
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY scratch scratch
COPY site site
RUN python -m scratch.build

FROM golang:1.26-alpine@sha256:ecb67f987aa1a57794c91d19ade7ae0209f2f0f5496aaef9e6ae85ddf92d02ab AS server
WORKDIR /build
COPY server/main.go .
RUN CGO_ENABLED=0 go build -trimpath -o /playground main.go

FROM scratch AS frozen-site
COPY --from=server /playground /playground
COPY --from=generator /app/dist /public
COPY datasets/v4/ /public/
USER 65534:65534
EXPOSE 8000
ENTRYPOINT ["/playground"]

FROM python:3.12-alpine AS integrated
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 MISSING_SCRATCH_RUNTIME=/data MS_PUBLIC_DIR=/public
COPY requirements-backend.txt .
RUN apk upgrade --no-cache && pip install --no-cache-dir -r requirements-backend.txt && mkdir -p /data && chown 65534:65534 /data
COPY backend/ backend/
COPY integrated_app.py .
COPY --from=frozen-site /public /public
USER 65534:65534
EXPOSE 8000
CMD ["python","-m","uvicorn","integrated_app:app","--host","0.0.0.0","--port","8000"]
