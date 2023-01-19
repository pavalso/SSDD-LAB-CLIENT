# Iceflix Client

Client to communicate with Iceflix microservices, in this case implemented as a CLI client.

It contains the following files and directories:

- `configs` has several configuration files.
- `iceflix` is the main Python package.
  You should rename it to something meaninful for your project.
- `iceflix/__init__.py` is an empty file needed by Python to
  recognise the `iceflix` directory as a Python module.
- `iceflix/cli.py` contains several functions to handle the basic console entry points
  defined in `python.cfg`.
  The name of the submodule and the functions can be modified if you need.
- `iceflix/iceflix.ice` contains the Slice interface definition for the lab.
- `pyproject.toml` defines the build system used in the project.
- `run_client` Its a script that can be run directly from the
  repository root directory. It runs the IceFlix client.
- `setup.cfg` is a Python distribution configuration file for Setuptools.
  It needs to be modified in order to adeccuate to the package name and
  console handler functions.

## Pre-requisites

To install this proyect you'll need to have installed python3.1x.

## Install (Linux)

1. Download or clone this repository.
2. Once the repository has been installed open a terminal in the repository SSDD-LAB-CLIENT.
3. Create a new environment `python3.1x -m venv venv`
4. Activate the new environment `./venv/bin/activate`
5. Install the package `pip install .`
6. Check correct installation `iceflix`

### DOCKER (optional)

You'll need to install (docker)[https://docs.docker.com/engine/install/] before.

Once installed:

This should allow you to execute the client in a docker environment

To create the docker container:
  1. `sudo docker build --tag {container_name}:{container_tag} .`
  2. `sudo docker run -it {container_name}:{container_tag}`

**zeroc-ice wheel may freeze for 5 or more minutes when building**

## Testing

Github actions is actually set to test automatically the code but in case you want to execute the [tests](tests/) by yourself you need to have installed [pytest-cov](https://pytest-cov.readthedocs.io/en/latest/).
Once installed you might want to use the [.coveragerc](tests/.coveragerc) included in the proyect to discard [cli.py](iceflix/cli.py)/[client.py](iceflix/client.py) files as those tests only focus on pure command functionality.

The above functionality can be achieved with: `pytest --cov-config .coveragerc --cov iceflix`
