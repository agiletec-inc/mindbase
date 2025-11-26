FROM node:24-bookworm

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      ca-certificates \
      git \
      curl \
      openssh-client \
      python3 \
      pkg-config \
      tini && \
    rm -rf /var/lib/apt/lists/*

# Ensure dedicated app user exists
RUN set -eux; \
    if ! id -u app >/dev/null 2>&1; then \
      useradd -m -s /bin/bash app; \
    fi; \
    chown -R app:app /home/app

# Pre-create common build directories to prevent root-owned creation by Docker volumes
RUN mkdir -p /app/{node_modules,.next,dist,build,out,.swc,.cache,.turbo} && \
    chown -R app:app /app

WORKDIR /app
USER app

ENTRYPOINT ["tini","--"]
CMD ["sleep","infinity"]
