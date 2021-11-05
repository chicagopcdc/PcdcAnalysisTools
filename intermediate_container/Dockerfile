# To run: docker run -v /path/to/wsgi.py:/var/www/PcdcAnalysisTools/wsgi.py --name=PcdcAnalysisTools -p 81:80 PcdcAnalysisTools
# To check running container: docker exec -it PcdcAnalysisTools /bin/bash

# FROM quay.io/pcdc/base_image:pcdc_dev_2021-11-03T09_23_27-05_00
# FROM quay.io/cdis/python:pybase3-2.0.0
FROM quay.io/pcdc/python:python3.8

# RUN apk update \
#     && apk add --upgrade --no-cache \
#         bash openssh curl ca-certificates openssl less htop g++ make wget rsync \
#         build-base libpng-dev freetype-dev libexecinfo-dev openblas-dev libgomp lapack-dev \
#                 libgcc libquadmath musl libgfortran lapack-dev \
#     && apk add --no-cache jpeg-dev zlib-dev \
#     && apk add postgresql-libs postgresql-dev libffi-dev libressl-dev \
#     && apk add linux-headers musl-dev gcc libxml2-dev libxslt-dev \
#     && apk add curl bash git vim 
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libffi-dev musl-dev gcc libxml2-dev libxslt-dev \
    curl bash git vim
    
COPY ./requirements.txt /PcdcAnalysisTools/
WORKDIR /PcdcAnalysisTools

# RUN python -m pip install --upgrade pip \
#     && python -m pip install --upgrade setuptools \
#     && pip --version \
#     && pip install numpy==1.17.3 \
#     && pip install scipy==1.3.1 \
#     && pip install -r requirements.txt
RUN python3 -m pip install --upgrade pip \
    && python3 -m pip install --upgrade setuptools \
    && python3 -m pip --version \
    && python3 -m pip install -r requirements.txt
    
