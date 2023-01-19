# Template project for ssdd-lab

This repository is a Python project template.
It contains the following files and directories:

- `configs` has several configuration files examples.
- `iceflix` is the main Python package.
  You should rename it to something meaninful for your project.
- `iceflix/__init__.py` is an empty file needed by Python to
  recognise the `iceflix` directory as a Python module.
- `iceflix/cli.py` contains several functions to handle the basic console entry points
  defined in `python.cfg`.
  The name of the submodule and the functions can be modified if you need.
- `iceflix/iceflix.ice` contains the Slice interface definition for the lab.
- `iceflix/main.py` has a minimal implementation of a service,
  without the service servant itself.
  Can be used as template for main or the other services.
- `pyproject.toml` defines the build system used in the project.
- `run_client` should be a script that can be run directly from the
  repository root directory. It should be able to run the IceFlix
  client.
- `run_service` should be a script that can be run directly from the
  repository root directory. It should be able to run all the services
  in background in order to test the whole system.
- `setup.cfg` is a Python distribution configuration file for Setuptools.
  It needs to be modified in order to adeccuate to the package name and
  console handler functions.

## TESTING

Github actions is actually set to test automatically the code but in case you want to execute the [tests](tests/) by yourself you need to have installed [pytest-cov](https://pytest-cov.readthedocs.io/en/latest/).
Once installed you might want to use the [.coveragerc](tests/.coveragerc) included in the proyect to discard [cli.py](iceflix/cli.py)/[client.py](iceflix/client.py) files asthose tests only focus on pure command functionality.

The above functionality can be achieved with: `pytest --cov-config .coveragerc --cov iceflix`

## DOCKER

This should allow you to execute the client in a docker environment

To create the docker container:
  1. sudo docker build --tag {container_name}:{container_tag} .
  2. sudo docker run -it {container_name}:{container_tag}

**zeroc-ice wheel may freeze for 5 or more minutes when building**
