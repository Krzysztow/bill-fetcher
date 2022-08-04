FROM zenika/alpine-chrome as base

USER root
RUN apk add --no-cache chromium-chromedriver && \
    apk add --no-cache python3 py3-pip

USER chrome

#================================================================================

FROM base as builder

COPY --chown=chrome:chrome . /wd

WORKDIR /wd/fetch-bill

ENV PIPENV_VENV_IN_PROJECT=1
RUN python3 -m pip install pipenv

RUN python3 -m pipenv install

#================================================================================

FROM base

WORKDIR /wd

COPY --from=builder /wd/fetch-bill /wd

ENV PATH="/wd/.venv/bin:$PATH"

ENTRYPOINT ["python3","./main_fetcher.py"]
