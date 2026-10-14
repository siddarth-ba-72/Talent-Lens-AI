# Single image: builds the React UI, then runs the FastAPI backend that serves it.
# Build from the repo root:
#   docker build --build-arg VITE_GOOGLE_CLIENT_ID=<client id> -t talentlens .

# --- UI build stage ---
FROM node:22-alpine AS ui
WORKDIR /repo/talentlens-client

COPY talentlens-client/package*.json ./
RUN npm ci

COPY talentlens-client/ ./

# Public OAuth client id, baked into the bundle at build time.
ARG VITE_GOOGLE_CLIENT_ID
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID

# Vite writes the build to ../talentlens-ai/static (see vite.config.ts).
RUN npm run build

# --- Run stage ---
FROM python:3.12-slim
WORKDIR /app

COPY talentlens-ai/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY talentlens-ai/app ./app
COPY --from=ui /repo/talentlens-ai/static ./static

RUN useradd --system --no-create-home talentlens
USER talentlens

# FORWARDED_ALLOW_IPS: which upstream hops may set X-Forwarded-For (it decides the
# client address used for login rate limiting). "*" suits a platform proxy that fronts
# every request; narrow it to the proxy's address range when that is known.
ENV APP_ENV=prod \
    PORT=9000 \
    FORWARDED_ALLOW_IPS=*

EXPOSE 9000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers"]
