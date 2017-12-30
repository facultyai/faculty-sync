import os.path
import subprocess

import sml.shell

from .ssh import sftp_from_ssh_details

SSH_OPTIONS = [
    '-o', 'IdentitiesOnly=yes',
    '-o', 'StrictHostKeyChecking=no',
    '-o', 'BatchMode=yes'
]


class Synchronizer(object):

    def __init__(self, local_dir, remote_dir, ssh_details):
        self.hostname = ssh_details.hostname
        self.port = ssh_details.port
        self.username = ssh_details.username
        self.key_file = ssh_details.key_file
        self.local_dir = local_dir
        self.remote_dir = remote_dir
        self._sftp = sftp_from_ssh_details(ssh_details)

    def up(self, path='', rsync_opts=None):
        if os.path.isabs(path):
            raise ValueError('path must be a relative path')
        remote = os.path.join(self.remote_dir, path)
        escaped_remote = sml.shell.quote(remote)
        local = os.path.join(self.local_dir, path)
        path_from = local
        path_to = u'{}@{}:{}'.format(
            self.username, self.hostname, escaped_remote)
        self._rsync(path_from, path_to, rsync_opts)

    def down(self, path='', rsync_opts=None):
        if os.path.isabs(path):
            raise ValueError('path must be a relative path')
        remote = os.path.join(self.remote_dir, path)
        escaped_remote = sml.shell.quote(remote)
        local = os.path.join(self.local_dir, path)
        path_from = u'{}@{}:{}'.format(
            self.username, self.hostname, escaped_remote)
        path_to = local
        self._rsync(path_from, path_to, rsync_opts)

    def rmfile_remote(self, path):
        self._sftp.remove(os.path.join(self.remote_dir, path))

    def _rsync(self, path_from, path_to, rsync_opts=None):
        rsync_opts = [] if rsync_opts is None else rsync_opts
        ssh_cmd = 'ssh {} -p {} -i {}'.format(
            ' '.join(SSH_OPTIONS), self.port, self.key_file
        )

        rsync_cmd = [
            'rsync', '-a', '-e', ssh_cmd,
            *rsync_opts, path_from, path_to
        ]

        process = _run_ssh_cmd(rsync_cmd)
        return process


def _run_ssh_cmd(argv):
    """Run a command and print a message when a string is matched."""
    process = subprocess.run(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    process.check_returncode()
    return process
