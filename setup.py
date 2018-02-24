from distutils.core import setup

version_ns = {}
with open(os.path.join(here, 'sml-sync', 'version.py')) as f:
    exec(f.read(), {}, version_ns)

setup(
    name='sml_sync',
    version=version_ns['version'],
    description='SherlockML file synchronizer',
    author='The SherlockML team',
    packages=['sml_sync', 'sml_sync.screens'],
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
