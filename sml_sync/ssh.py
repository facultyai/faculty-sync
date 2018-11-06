import contextlib
import os
import shutil
import stat
import tempfile

import paramiko
import sml.galleon

from .models import SshDetails


def sftp_from_ssh_details(ssh_details):
    transport = paramiko.Transport((ssh_details.hostname, ssh_details.port))
    transport.connect(
        username=ssh_details.username,
        pkey=paramiko.rsakey.RSAKey.from_private_key_file(
            ssh_details.key_file
        ),
    )
    sftp = paramiko.sftp_client.SFTPClient.from_transport(transport)
    return sftp


@contextlib.contextmanager
def get_ssh_details(configuration):
    client = sml.galleon.Galleon()
    details = client.ssh_details(
        configuration.project.id_, configuration.server_id
    )
    hostname = details["hostname"]
    port = details["port"]
    username = details["username"]
    key = details["key"]
    with _save_key_to_file(key) as key_file:
        ssh_details = SshDetails(hostname, port, username, key_file)
        yield ssh_details


@contextlib.contextmanager
def _save_key_to_file(key):
    tmpdir = tempfile.mkdtemp()
    filename = os.path.join(tmpdir, "key.pem")
    with open(filename, "w") as keyfile:
        keyfile.write(key)
    os.chmod(filename, stat.S_IRUSR & ~stat.S_IRGRP & ~stat.S_IROTH)
    yield filename
    shutil.rmtree(tmpdir)
