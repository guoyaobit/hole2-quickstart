FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install minimal OS tools for downloading and extracting the HOLE tarball
RUN apt-get update \
 && apt-get install -y --no-install-recommends wget ca-certificates tar gzip \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project files into the image (image will contain source in /app)
COPY . /app

# Install Python dependencies and Jupyter Notebook via pip to keep image small
RUN pip install --no-cache-dir matplotlib pandas ipywidgets pexpect PyYAML jupyter

# Install HOLE toolchain from official tarball into /opt/hole2 (static binaries)
RUN wget -O /tmp/hole2.tar.gz http://www.holeprogram.org/downloads/2.2.005/hole2-ApacheLicense-2.2.005-Linux-x86_64.tar.gz \
 && mkdir -p /opt/hole2 \
 && tar xf /tmp/hole2.tar.gz -C /opt \
 && rm -f /tmp/hole2.tar.gz

# Ensure HOLE binaries are on PATH
ENV PATH="/opt/hole2/exe:${PATH}"

EXPOSE 8888

# Default: start Jupyter Notebook so users open run.ipynb in the browser
CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]
