# FROM quay.io/pcdc/pcdcanalysistools_intermediate:improve_base_image_Thu__04_Nov_2021_16_36_28_GMT
FROM quay.io/pcdc/pcdcanalysistools_intermediate:improve_base_image_Fri__05_Nov_2021_18_50_41_GMT

COPY . /PcdcAnalysisTools
COPY ./deployment/uwsgi/uwsgi.ini /etc/uwsgi/uwsgi.ini
WORKDIR /PcdcAnalysisTools

# RUN pip install -r requirements.txt
RUN python3 /PcdcAnalysisTools/setup.py install \
    && python3 -m pip install -r requirements.txt

RUN mkdir -p /var/www/PcdcAnalysisTools \
    && mkdir /run/ngnix/ \
    && chown nginx /var/www/PcdcAnalysisTools

EXPOSE 80

RUN COMMIT=`git rev-parse HEAD` && echo "COMMIT=\"${COMMIT}\"" >PcdcAnalysisTools/version_data.py \
    && VERSION=`git describe --always --tags` && echo "VERSION=\"${VERSION}\"" >>PcdcAnalysisTools/version_data.py \
    && python3 setup.py install

WORKDIR /var/www/PcdcAnalysisTools

CMD /dockerrun.sh
