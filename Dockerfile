FROM mambaorg/micromamba:2.10.0

COPY --chown=$MAMBA_USER:$MAMBA_USER environment.yml /tmp/environment.yml
RUN micromamba install --yes --name base --strict-channel-priority --file /tmp/environment.yml \
    && micromamba clean --all --yes

# docker exec bypasses micromamba's entrypoint activation. Make the base
# environment tools available to both the main process and exec commands.
ENV PATH=/opt/conda/bin:$PATH \
    PYTHONPATH=/opt/hole2 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg \
    MPLCONFIGDIR=/tmp/hole2-matplotlib \
    JUPYTER_CONFIG_DIR=/tmp/hole2-jupyter/config \
    JUPYTER_RUNTIME_DIR=/tmp/hole2-jupyter/runtime \
    HOME=/tmp

WORKDIR /opt/hole2
COPY --chown=$MAMBA_USER:$MAMBA_USER run_holeprogram.py run_notebook.py colab_support.py run.ipynb colab.ipynb LICENSE ./
COPY --chown=$MAMBA_USER:$MAMBA_USER docker/ ./docker/
COPY --chown=$MAMBA_USER:$MAMBA_USER tests/ ./tests/

RUN micromamba run --name base python docker/check_environment.py \
    && micromamba run --name base python -m unittest discover -s tests -v

USER root
RUN mkdir -p /data && chmod 1777 /data
USER $MAMBA_USER
WORKDIR /data

EXPOSE 8888
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD ["/opt/conda/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8888/login', timeout=3).close()"]

# Keep micromamba's inherited entrypoint so base is activated at runtime.
CMD ["python", "/opt/hole2/docker/start.py"]
