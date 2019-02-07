import os

from setuptools import find_packages, setup

here = os.path.dirname(os.path.abspath(__file__))

version_ns = {}
with open(os.path.join(here, "faculty_sync", "version.py")) as f:
    exec(f.read(), {}, version_ns)

setup(
    name="faculty_sync",
    version=version_ns["version"],
    description="Faculty Platform file synchronizer",
    author="Faculty",
    author_email="opensource@faculty.ai",
    packages=find_packages(),
    entry_points={"console_scripts": ["faculty-sync=faculty_sync:run"]},
    install_requires=[
        "faculty",
        "daiquiri",
        "paramiko",
        "watchdog",
        "semantic_version",
        "prompt_toolkit>=2.0",
    ],
    classifiers=[
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
    ],
)
