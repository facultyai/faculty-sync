import os
from distutils.core import setup

here = os.path.dirname(os.path.abspath(__file__))

version_ns = {}
with open(os.path.join(here, 'sml_sync', 'version.py')) as f:
    exec(f.read(), {}, version_ns)

setup(
    name='sml_sync',
    version=version_ns['version'],
    description='SherlockML file synchronizer',
    author='ASI Data Science',
    packages=['sml_sync', 'sml_sync.screens'],
    entry_points={
        'console_scripts': ['sml-sync=sml_sync:run']
    },
    # prompt_toolkit 2.0 is currently only available from github:
    dependency_links=['https://github.com/'
                      'jonathanslenders/python-prompt-toolkit/'
                      'tarball/2.0#egg=prompt_toolkit-2.0'],
    install_requires=[
        'sml',
        'daiquiri',
        'paramiko',
        'inflect',
        'watchdog',
        'semantic_version',
        'prompt_toolkit>=2.0'
    ]
)
