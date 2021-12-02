# To run: docker run -v /path/to/wsgi.py:/var/www/PcdcAnalysisTools/wsgi.py --name=PcdcAnalysisTools -p 81:80 PcdcAnalysisTools
# To check running container: docker exec -it PcdcAnalysisTools /bin/bash

# FROM quay.io/pcdc/base_image:pcdc_dev_2021-11-03T09_23_27-05_00
# FROM quay.io/cdis/python:pybase3-2.0.0
FROM quay.io/pcdc/python:python3.8

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
