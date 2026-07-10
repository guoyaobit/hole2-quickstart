FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends wget ca-certificates tar gzip \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project files
COPY . /app

# Python deps used by the project (adjust if you add requirements file)
RUN pip install --no-cache-dir matplotlib pandas ipywidgets pexpect PyYAML

# Install HOLE toolchain (matches install_hole.sh)
RUN wget -O /tmp/hole2.tar.gz http://www.holeprogram.org/downloads/2.2.005/hole2-ApacheLicense-2.2.005-Linux-x86_64.tar.gz \
 && tar xf /tmp/hole2.tar.gz -C /root/ \
 && rm /tmp/hole2.tar.gz

ENV PATH="/root/hole2/exe:${PATH}"

EXPOSE 8888

# Default: start Jupyter Notebook so the existing run.ipynb can be used in container
CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]
