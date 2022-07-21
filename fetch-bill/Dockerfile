FROM zenika/alpine-chrome

USER root
RUN apk add --no-cache chromium-chromedriver && \
    apk add --no-cache python3 py3-pip 

USER chrome
#ENV PYTHONPATH /home/chrome/.local/lib/python3.10/site-packages
RUN python3 -m pip install pipenv


WORKDIR /wd

COPY . /wd

# install globally, a really pipenv is only for local development
# docker is already a sandbox itself
RUN python3 -m pipenv install --system

ENTRYPOINT ["python3","./main.py"]