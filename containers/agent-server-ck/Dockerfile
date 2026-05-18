ARG AGENT_SERVER_IMAGE=ghcr.io/openhands/agent-server:1.22.1-python
FROM ${AGENT_SERVER_IMAGE}

ARG TARGETARCH
ARG CONTEXT_KING_VERSION=v1.8.3
ARG DOTNET_CHANNEL=10.0

ENV DEBIAN_FRONTEND=noninteractive
ENV CK_HOME=/root/.ck
ENV CK_MODEL_DIR=/root/.ck/models/bge-small-en-v1.5

# Context King Linux binaries are framework-dependent apphosts, so install
# a matching .NET runtime in the sandbox image.
USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash ca-certificates curl tar \
    && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    curl -fsSL https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh; \
    bash /tmp/dotnet-install.sh --channel "${DOTNET_CHANNEL}" --runtime dotnet --install-dir /usr/share/dotnet; \
    ln -sf /usr/share/dotnet/dotnet /usr/local/bin/dotnet; \
    rm -f /tmp/dotnet-install.sh

RUN set -eux; \
    arch="${TARGETARCH:-}"; \
    if [ -z "${arch}" ]; then \
      case "$(uname -m)" in \
        x86_64|amd64) arch="amd64" ;; \
        aarch64|arm64) arch="arm64" ;; \
        *) echo "Unsupported architecture: $(uname -m)"; exit 1 ;; \
      esac; \
    fi; \
    case "${arch}" in \
      amd64) ck_arch="linux-x64" ;; \
      arm64) ck_arch="linux-arm64" ;; \
      *) echo "Unsupported TARGETARCH: ${arch}"; exit 1 ;; \
    esac; \
    curl -fsSL \
      -o /tmp/context-king.tar.gz \
      "https://github.com/Fredrik-C/ContextKing/releases/download/${CONTEXT_KING_VERSION}/context-king-${ck_arch}.tar.gz"; \
    mkdir -p /opt/contextking "${CK_HOME}/bin" "${CK_HOME}/models" /root/.agents/skills; \
    tar -xzf /tmp/context-king.tar.gz -C /opt/contextking --strip-components=1; \
    cp "/opt/contextking/skills/ck/ck-${ck_arch}" "${CK_HOME}/bin/ck"; \
    chmod +x "${CK_HOME}/bin/ck"; \
    cp -r /opt/contextking/models/bge-small-en-v1.5 "${CK_HOME}/models/"; \
    cp -r /opt/contextking/skills/* /root/.agents/skills/; \
    find /root/.agents/skills -name SKILL.md -type f -exec sed -i \
      -e "s|\\.claude/skills/ck/ck |${CK_HOME}/bin/ck |g" \
      -e "s|\\.claude\\\\skills\\\\ck\\\\ck\\.cmd |${CK_HOME}/bin/ck |g" \
      -e "s|\\.claude/skills/ck/ck$|${CK_HOME}/bin/ck|g" \
      {} +; \
    ln -sf "${CK_HOME}/bin/ck" /usr/local/bin/ck; \
    rm -f /tmp/context-king.tar.gz

RUN ck --version && dotnet --info > /dev/null
