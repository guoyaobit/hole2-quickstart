# Multi-stage build: install deps and HOLE in builder, copy only runtime files into final image
FROM python AS builder

ENV DEBIAN_FRONTEND=noninteractive

# Minimal tools to download and extract HOLE
RUN apt-get update \
 && apt-get install -y --no-install-recommends wget ca-certificates tar gzip \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp

# Upgrade pip and install Python packages into the image's /usr/local (default)
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir matplotlib pandas ipywidgets pexpect PyYAML jupyterlab

# Download and extract HOLE into /root/hole2
RUN wget -O /tmp/hole2.tar.gz http://www.holeprogram.org/downloads/2.2.005/hole2-ApacheLicense-2.2.005-Linux-x86_64.tar.gz \
 && mkdir -p /root/hole2 \
 && tar xf /tmp/hole2.tar.gz -C /root \
 && rm -f /tmp/hole2.tar.gz

# Final image: start from a clean slim image and copy only the runtime artifacts
FROM python

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Copy installed Python packages and HOLE binaries from the builder stage
COPY --from=builder /usr/local /usr/local
COPY --from=builder /root/hole2 /root/hole2

# Copy project source into /app
COPY . /app

# Ensure HOLE binaries are on PATH
ENV PATH="/root/hole2/exe:${PATH}"

EXPOSE 8888

# Default: start Jupyter Lab so users open run.ipynb in the browser
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]
