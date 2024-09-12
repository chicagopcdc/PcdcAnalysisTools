import os
from boto.s3.connection import OrdinaryCallingFormat
from os import environ as env

APP_NAME = 'PcdcAnalysisTools'
SERVICE_NAME = 'pcdcanalysistools'
PRIVATE_KEY_PATH = "/var/www/PcdcAnalysisTools/jwt_private_key.pem"


# Auth
AUTH = "https://gdc-portal.nci.nih.gov/auth/keystone/v3/"
INTERNAL_AUTH = env.get("INTERNAL_AUTH", "https://gdc-portal.nci.nih.gov/auth/")

AUTH_ADMIN_CREDS = {
    "domain_name": env.get("KEYSTONE_DOMAIN"),
    "username": env.get("KEYSTONE_USER"),
    "password": env.get("KEYSTONE_PASSWORD"),
    "auth_url": env.get("KEYSTONE_AUTH_URL"),
    "user_domain_name": env.get("KEYSTONE_DOMAIN"),
}

# Storage
CLEVERSAFE_HOST = env.get("CLEVERSAFE_HOST", "cleversafe.service.consul")

STORAGE = {
    "s3": {
        "keys": {
            "cleversafe.service.consul": {
                "access_key": os.environ.get("CLEVERSAFE_ACCESS_KEY"),
                "secret_key": os.environ.get("CLEVERSAFE_SECRET_KEY"),
            },
            "localhost": {
                "access_key": os.environ.get("CLEVERSAFE_ACCESS_KEY"),
                "secret_key": os.environ.get("CLEVERSAFE_SECRET_KEY"),
            },
        },
        "kwargs": {
            "cleversafe.service.consul": {
                "host": "cleversafe.service.consul",
                "is_secure": False,
                "calling_format": OrdinaryCallingFormat(),
            },
            "localhost": {
                "host": "localhost",
                "is_secure": False,
                "calling_format": OrdinaryCallingFormat(),
            },
        },
    }
}
SUBMISSION = {"bucket": "test_submission", "host": CLEVERSAFE_HOST}


# API server
SHEEPDOG_HOST = os.getenv("SHEEPDOG_HOST", "localhost")
SHEEPDOG_PORT = int(os.getenv("SHEEPDOG_PORT", "5000"))

# FLASK_SECRET_KEY should be set to a secure random string with an appropriate
# length; 50 is reasonable. For the random generation to be secure, use
# ``random.SystemRandom()``
FLASK_SECRET_KEY = "eCKJOOw3uQBR5pVDz3WIvYk3RsjORYoPRdzSUNJIeUEkm1Uvtq"

DICTIONARY_URL = os.environ.get(
    "DICTIONARY_URL",
    "https://s3.amazonaws.com/dictionary-artifacts/datadictionary/develop/schema.json",
)

GUPPY_API = "http://portal-dev.pedscommons.org/guppy"

USER_API = "http://portal-dev.pedscommons.org/user/"
OIDC_ISSUER = "http://portal-dev.pedscommons.org"
OAUTH2 = {
    "client_id": os.environ.get("CDIS_GDCAPI_CLIENT_ID"),
    "client_secret": os.environ.get("CDIS_GDCAPI_CLIENT_SECRET"),
    "api_base_url": USER_API,
    "authorize_url": "http://portal-dev.pedscommons.org/user/oauth2/authorize",
    "access_token_url": "http://portal-dev.pedscommons.org/user/oauth2/token",
    "refresh_token_url": "http://portal-dev.pedscommons.org/user/oauth2/token",
    "client_kwargs": {
        "redirect_uri": os.environ.get(
            "CDIS_GDCAPI_OAUTH_REDIRECT", "http://portal-dev.pedscommons.org/api/v0/oauth2/authorize"
        ),
        "scope": "openid data user",
    },
}

SESSION_COOKIE_NAME = "sheepdog_session"
# verify project existence in dbgap or not
VERIFY_PROJECT = False
AUTH_SUBMISSION_LIST = False
# dev setup use http
os.environ["AUTHLIB_INSECURE_TRANSPORT"] = "true"


# excluded_variables nested paths may be a problem if a variable in another path has the same name as the one in this path
SURVIVAL = {
    'consortium': ["INSTRuCT"],
    'excluded_variables': [
        {
            'label': 'Data Contributor',
            'field': 'data_contributor_id',
        },
        {
            'label': 'Study',
            'field': 'studies.study_id',
        },
        {
            'label': 'Treatment Arm',
            'field': 'studies.treatment_arm',
        }
    ],
    'result': {
        'risktable': True,
        'survival': True
    }
}

EXTERNAL = {
    'commons': [
        {
            'label': 'Genomic Data Commons',
            'value': 'gdc'
        },
        {
            'label': 'Gabriella Miller Kids First',
            'value': 'gmkf'
        },
        {
            'label': 'Common Data Service',
            'value': 'cds'
        }
    ], 
    "commons_dict": {
        "gdc": "TARGET - GDC", 
        "gmkf": "GMKF", 
        "cds": "CDS"
    }
}
