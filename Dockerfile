# The whole product ships as one image: the API and the built interface.
# The interface is compiled in a first stage and copied next to the package,
# so the backend can serve it from a single origin without any extra service.
# The worker runs from the very same image with a different command.

FROM node:20-alpine AS interface

WORKDIR /build

COPY src/frontend/package.json src/frontend/package-lock.json ./
RUN npm ci

COPY src/frontend/ ./
RUN npm run build


FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FRONTEND_DIST=/app/src/frontend/dist

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY build/migrations ./build/migrations
COPY --from=interface /build/dist ./src/frontend/dist

RUN pip install --no-cache-dir .

EXPOSE 8000 8001

CMD ["python", "-m", "backend.main"]
