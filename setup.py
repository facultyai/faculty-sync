from distutils.core import setup

setup(
    name='sml_sync',
    version='0.1.0-dev',
    description='SherlockML file synchronizer',
    author='The SherlockML team',
    entry_points={
        'console_scripts': ['sml-sync=sml_sync:run']
    },
    install_requires=[
        'sml',
        'daiquiri',
        'paramiko',
        'inflect',
        'watchdog',
        # This is currently missing prompt-toolkit (waiting for 2.0 to be released)
    ]
)
