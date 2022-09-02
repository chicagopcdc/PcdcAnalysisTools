# To run: docker run -v /path/to/wsgi.py:/var/www/PcdcAnalysisTools/wsgi.py --name=PcdcAnalysisTools -p 81:80 PcdcAnalysisTools
# To check running container: docker exec -it PcdcAnalysisTools /bin/bash

FROM quay.io/pcdc/base_image:pcdc_dev_2021-11-03T09_23_27-05_00

RUN apk update \
    && apk add --upgrade --no-cache \
        bash openssh curl ca-certificates openssl less htop g++ make wget rsync \
        build-base libpng-dev freetype-dev libexecinfo-dev openblas-dev libgomp lapack-dev \
                libgcc libquadmath musl libgfortran lapack-dev \
    && apk add --no-cache jpeg-dev zlib-dev \
    && apk add postgresql-libs postgresql-dev libffi-dev libressl-dev \
    && apk add linux-headers musl-dev gcc libxml2-dev libxslt-dev \
    && apk add curl bash git vim 

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
