#!/bin/bash

nginx 
poetry run gunicorn -c "/PcdcAnalysisTools/deployment/wsgi/gunicorn.conf.py"