# PCDC Analysis tool

## Installation

### For Development

```bash
python -m venv env
source env/bin/activate
poetry install
python run.py
deactivate
```

### For Development

build the container
```bash
docker build -t pcdcanalysistools:test .
```

add the container in the revproxy conf and in the docker-compose.yml file

## Documentation

### Sphinx

Auto-documentation is set up using
[Sphinx](http://www.sphinx-doc.org/en/stable/). To build it, run
```bash
cd docs
make html
```
which by default will output the `index.html` page to
`docs/build/html/index.html`.

### Swagger

[OpenAPI documentation available here.](http://petstore.swagger.io/?url=https://raw.githubusercontent.com/uc-cdis/sheepdog/master/openapi/swagger.yml)

The YAML file comtaining the OpenAPI documentation is in the `openapi` folder;
see the README in that folder for more details.


## End Point Tests
python -m venv env
source env/bin/activate
poetry install

create .env file:
    Full_DATA_PATH = 'test_data\data.json'
    SHORT_DATA_PATH = 'test_data\data_short.json'
    NO_DATA_PATH = 'test_data\no_data.json'
    DATA_PATH = 'test_data\data_short_stats.json'
    Short_DATA_SURVIVAL_PATH = 'test_data\data_short_survival.json'
    Short_DATA_STATS_PATH = 'test_data\data_short_stats.json'
    MOCK_DATA = 'True'

if MOCK_DATA does not equal true then data will come from guppy data otherwise data will come from mock data from json files

pytest tests\endpoint.py

