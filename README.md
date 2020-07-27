# PCDC Analysis tool

## Installation

### For Development

```bash
python -m venv env
source env/bin/activate
pip install -r dev-requirements.txt
python setup.py develop
python run.py
deactivate
```

(`dev-requirements.txt` contains requirements for testing and doc generation.
Installing with `python setup.py develop` avoids literally installing anything
but creates an egg link to the source code.)

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

