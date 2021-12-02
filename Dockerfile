FROM quay.io/pcdc/pcdcanalysistools_intermediate:improve_base_image_Thu__02_Dec_2021_18_38_44_GMT

COPY . /PcdcAnalysisTools
COPY ./deployment/uwsgi/uwsgi.ini /etc/uwsgi/uwsgi.ini
WORKDIR /PcdcAnalysisTools

# upgrade pip + poetry
RUN pip install --upgrade pip \
    && pip install --upgrade poetry 

COPY pyproject.toml poetry.lock /PcdcAnalysisTools/

# RUN source $HOME/.poetry/env \
RUN poetry config virtualenvs.create false \
    && poetry install -vv --no-dev --no-interaction \
    && pip --version \
    && poetry show -v

RUN mkdir -p /var/www/PcdcAnalysisTools \
    && mkdir /run/ngnix/ \
    && chown nginx /var/www/PcdcAnalysisTools

EXPOSE 80

RUN COMMIT=`git rev-parse HEAD` && echo "COMMIT=\"${COMMIT}\"" >PcdcAnalysisTools/version_data.py \
    && VERSION=`git describe --always --tags` && echo "VERSION=\"${VERSION}\"" >>PcdcAnalysisTools/version_data.py \
    && python3 setup.py install

WORKDIR /var/www/PcdcAnalysisTools

CMD /dockerrun.sh
