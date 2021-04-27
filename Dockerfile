FROM quay.io/pcdc/pcdcanalysistools_intermediate:pcdc_dev_2021-04-08T12_37_25-05_00

COPY . /PcdcAnalysisTools
COPY ./deployment/uwsgi/uwsgi.ini /etc/uwsgi/uwsgi.ini
WORKDIR /PcdcAnalysisTools

RUN pip install -r requirements.txt

RUN mkdir -p /var/www/PcdcAnalysisTools \
    && mkdir /run/ngnix/ \
    && chown nginx /var/www/PcdcAnalysisTools

EXPOSE 80

RUN COMMIT=`git rev-parse HEAD` && echo "COMMIT=\"${COMMIT}\"" >PcdcAnalysisTools/version_data.py \
    && VERSION=`git describe --always --tags` && echo "VERSION=\"${VERSION}\"" >>PcdcAnalysisTools/version_data.py \
    && python setup.py install

WORKDIR /var/www/PcdcAnalysisTools

CMD /dockerrun.sh
