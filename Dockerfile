ARG PYTHON_VERSION=3.8-alpine

FROM library/python:${PYTHON_VERSION}

COPY . /usr/src/app

WORKDIR /usr/src/app

RUN pip install -e ./
