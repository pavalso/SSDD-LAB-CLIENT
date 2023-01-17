FROM python:3.10-slim@sha256:6164f21505159a6a36909e06ab5ab6910c0c370117d165154da09e1eff88c52d

RUN python -m venv /usr/iceflix/venv
ENV PATH="/usr/app/venv/bin:$PATH"

RUN apt-get update
RUN apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libbz2-dev \
    python3-dev

WORKDIR /usr/iceflix

COPY iceflix/* ./iceflix/
COPY configs/*.config ./configs/
COPY run_client ./
COPY setup.cfg ./
COPY pyproject.toml ./

RUN pip install .

ENTRYPOINT [ "iceflix" ]
