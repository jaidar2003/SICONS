FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m buildwise
USER buildwise
WORKDIR /home/buildwise/app
ENV PATH="/home/buildwise/.local/bin:${PATH}"
ENV CMDSTAN=/home/buildwise/.cmdstan/cmdstan-2.38.0

COPY --chown=buildwise:buildwise requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt
ARG INSTALL_CMDSTAN=true
RUN if [ "$INSTALL_CMDSTAN" = "true" ]; then \
        python -c "import cmdstanpy; cmdstanpy.install_cmdstan(version='2.38.0', cores=2)"; \
    fi

COPY --chown=buildwise:buildwise . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
