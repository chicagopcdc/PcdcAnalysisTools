# To run: docker run -v /path/to/wsgi.py:/var/www/PcdcAnalysisTools/wsgi.py --name=PcdcAnalysisTools -p 81:80 PcdcAnalysisTools
# To check running container: docker exec -it PcdcAnalysisTools /bin/bash

# FROM quay.io/cdis/python-nginx:pybase3-1.1.0
FROM base_image:test

RUN apk update \
    && apk add --upgrade --no-cache \
        bash openssh curl ca-certificates openssl less htop g++ make wget rsync \
        build-base libpng-dev freetype-dev libexecinfo-dev openblas-dev libgomp lapack-dev \
                libgcc libquadmath musl libgfortran lapack-dev \
    && apk add --no-cache jpeg-dev zlib-dev \
    && apk add postgresql-libs postgresql-dev libffi-dev libressl-dev \
    && apk add linux-headers musl-dev gcc libxml2-dev libxslt-dev \
    && apk add curl bash git vim 
#   && apk add --no-cache --virtual .build-deps build-base linux-headers  

#   RUN pip install pillow  

#   RUN apk del .build-deps

COPY . /PcdcAnalysisTools
COPY ./deployment/uwsgi/uwsgi.ini /etc/uwsgi/uwsgi.ini
WORKDIR /PcdcAnalysisTools

RUN python -m pip install --upgrade pip \
    && python -m pip install --upgrade setuptools \
    && pip --version \
    && pip install numpy==1.17.3 \
    && pip install scipy==1.3.1 \
#    && pip install --no-cache-dir -r requirements.txt 
    && pip install -r requirements.txt
    # && pip install -r spec_requirements.txt --no-deps

RUN mkdir -p /var/www/PcdcAnalysisTools \
    && mkdir /run/ngnix/ \
    && chown nginx /var/www/PcdcAnalysisTools

EXPOSE 80

RUN COMMIT=`git rev-parse HEAD` && echo "COMMIT=\"${COMMIT}\"" >PcdcAnalysisTools/version_data.py \
    && VERSION=`git describe --always --tags` && echo "VERSION=\"${VERSION}\"" >>PcdcAnalysisTools/version_data.py \
    && python setup.py install

WORKDIR /var/www/PcdcAnalysisTools

CMD /dockerrun.sh
