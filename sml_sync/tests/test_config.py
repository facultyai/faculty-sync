import tempfile
from contextlib import contextmanager
from pathlib import Path

from ..config import get_config, FileConfiguration

@contextmanager
def _temporary_configurations(user_config=None, project_config=None):
    with tempfile.TemporaryDirectory() as temporary_directory:
        path = Path(temporary_directory)
        user_configuration_path = path / 'user.conf'
        project_configuration_path = path / 'project.conf'
        if user_config is not None:
            with user_configuration_path.open('w') as fp:
                fp.write(user_config)
        if project_config is not None:
            with project_configuration_path.open('w') as fp:
                fp.write(project_config)
        yield (project_configuration_path, user_configuration_path)


def test_project_config():
    configuration_file_value = """
    [default]
    project = acme
    remote = /project/dir22
    """
    with _temporary_configurations(
            project_config=configuration_file_value
    ) as (project_path, user_path):
        result = get_config('local-directory', project_path, user_path)
        assert result == FileConfiguration('acme', '/project/dir22', None, [])
