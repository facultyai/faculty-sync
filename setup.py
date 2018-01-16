from distutils.core import setup

setup(
    name='sml_sync',
    version='0.1.0',
    description='SherlockML file synchronizer',
    author='The SherlockML team',
    entry_points={
        'console_scripts': ['sml-sync=sml_sync:run']
    },
)
