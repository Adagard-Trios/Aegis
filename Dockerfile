# MedVerse FastAPI backend — multi-stage Dockerfile.
#
# Built for Render's Docker runtime, but portable to any container
# host (Fly.io, Cloud Run, ECS). Render auto-detects this and uses
# it instead of the buildpack when present.
#
# Two-stage build keeps the runtime image small (~1.1 GB vs ~2.5 GB
# without the staging) by leaving build tools + pip caches behind.

# ── Stage 1: build ──────────────────────────────────────────────────
FROM python:3.13-slim AS build

# OS-level build dependencies for the wheels we install:
#  - build-essential, gcc: scipy / numpy / fftea / scikit-learn
#  - libpq-dev: psycopg2-binary fallback for non-binary wheels
#  - libffi-dev / libssl-dev: cryptography (PyJWT)
#  - ffmpeg: librosa / audio I/O (icbhi adapter, lung_sound)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libpq-dev \
        libffi-dev \
        libssl-dev \
        ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Build wheels into /wheels so the runtime stage can pip-install
# from the local cache without re-downloading anything.
WORKDIR /build
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


# ── Stage 2: runtime ────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

# Runtime-only OS deps. ffmpeg stays for the audio adapters; libpq5
# is the binary half of psycopg2-binary (no -dev headers needed).
# gosu lets the entrypoint chown the persistent disk as root, then
# drop privileges to the medverse user before exec'ing the app.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libpq5 \
        gosu \
    && rm -rf /var/lib/apt/lists/*

# Drop privileges — Render runs containers as root by default but
# defensive defaults never hurt.
RUN useradd --create-home --uid 1000 medverse
WORKDIR /app

# Install pre-built wheels from the build stage.
COPY --from=build /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

# Application code. Heavy paths excluded via .dockerignore (frontend,
# mobile, models data caches, .pio firmware build artefacts).
COPY --chown=medverse:medverse . .

# Entrypoint must run as root so it can chown the persistent disk
# (Render mounts disks root-owned; the medverse user can't write
# without help). The script drops to medverse via gosu before exec'ing
# the app — see docker-entrypoint.sh.
COPY --chmod=0755 docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

# Render injects $PORT; default 8000 for local docker run.
ENV PORT=8000

# Expose the port for documentation. Render ignores this and uses
# the value of $PORT directly.
EXPOSE 8000

# Migrations run at start, not build — the DB env (MEDVERSE_DB_URL)
# isn't available during image build. Idempotent: alembic skips
# already-applied revisions. The entrypoint also chowns the persistent
# disk so the unprivileged app user can write Chroma + uploads + SQLite.
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
