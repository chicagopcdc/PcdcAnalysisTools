# To run: docker run -v /path/to/wsgi.py:/var/www/PcdcAnalysisTools/wsgi.py --name=PcdcAnalysisTools -p 81:80 PcdcAnalysisTools
# To check running container: docker exec -it PcdcAnalysisTools /bin/bash

FROM quay.io/pcdc/python:python3.10_2021-12-02T11_35_14-06_00

# upgrade pip + poetry
RUN pip install --upgrade pip \
    && pip install --upgrade poetry 

COPY pyproject.toml poetry.lock /PcdcAnalysisTools/

WORKDIR /PcdcAnalysisTools

# RUN source $HOME/.poetry/env \
RUN poetry config virtualenvs.create false \
    && poetry install -vv --no-dev --no-interaction \
    && pip --version \
    && poetry show -v
