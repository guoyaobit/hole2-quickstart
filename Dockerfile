FROM continuumio/miniconda3:latest

WORKDIR /app

# Copy project files
COPY . /app

# Use conda to install Python 3.12 and HOLE + Python deps from conda-forge
RUN conda update -n base -c defaults conda -y \
 && conda install -y -c conda-forge \
    python=3.12 \
    hole2 \
    matplotlib \
    pandas \
    ipywidgets \
    pexpect \
    jupyter \
 && conda clean -afy

ENV PATH="/opt/conda/bin:${PATH}"

EXPOSE 8888

# Default: start Jupyter Notebook so the existing run.ipynb can be used in container
CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]
