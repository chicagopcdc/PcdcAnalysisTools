# To run: docker run -v /path/to/wsgi.py:/var/www/PcdcAnalysisTools/wsgi.py --name=PcdcAnalysisTools -p 81:80 PcdcAnalysisTools
# To check running container: docker exec -it PcdcAnalysisTools /bin/bash

FROM quay.io/cdis/python-nginx:pybase3-1.1.0

RUN apk update \
    && apk add postgresql-libs postgresql-dev libffi-dev libressl-dev \
    && apk add linux-headers musl-dev gcc libxml2-dev libxslt-dev \
    && apk add curl bash git vim

COPY . /PcdcAnalysisTools
COPY ./deployment/uwsgi/uwsgi.ini /etc/uwsgi/uwsgi.ini
WORKDIR /PcdcAnalysisTools

RUN python -m pip install --upgrade pip \
    && python -m pip install --upgrade setuptools \
    && pip --version \
    && pip install -r requirements.txt

RUN mkdir -p /var/www/PcdcAnalysisTools \
    && mkdir /run/ngnix/ \
    && chown nginx /var/www/PcdcAnalysisTools

EXPOSE 80

RUN COMMIT=`git rev-parse HEAD` && echo "COMMIT=\"${COMMIT}\"" >PcdcAnalysisTools/version_data.py \
    && VERSION=`git describe --always --tags` && echo "VERSION=\"${VERSION}\"" >>PcdcAnalysisTools/version_data.py \
    && python setup.py install

WORKDIR /var/www/PcdcAnalysisTools

CMD /dockerrun.sh
