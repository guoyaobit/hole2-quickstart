FROM condaforge/mambaforge:latest

WORKDIR /app

# Copy project files early for rebuildability
COPY . /app

# Install HOLE and Python deps via conda (conda-forge) for reproducible environment
# Use mamba (installed in mambaforge) for speed
RUN mamba install -y -c conda-forge \
    python=3.11 \
    hole2 \
    matplotlib \
    pandas \
    ipywidgets \
    pexpect \
    jupyter \
  && mamba clean -afy

ENV PATH="/opt/conda/bin:${PATH}"

EXPOSE 8888

# Default: start Jupyter Notebook so the existing run.ipynb can be used in container
CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]
