FROM quay.io/pcdc/pcdcanalysistools_intermediate:pcdc_dev_2021-04-05T16_38_58-05_00
# pcdc_dev_Thu__17_Sep_2020_14_09_07_GMT

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
