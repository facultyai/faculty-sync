import os.path
import subprocess
from datetime import datetime
import logging
import time

import sml.shell

from .ssh import sftp_from_ssh_details
from .models import FsObject, FsObjectType, DirectoryAttrs, FileAttrs

SSH_OPTIONS = [
    '-o', 'IdentitiesOnly=yes',
    '-o', 'StrictHostKeyChecking=no',
    '-o', 'BatchMode=yes'
]


class Synchronizer(object):

    def __init__(self, local_dir, remote_dir, ssh_details, ignore_paths):
        self.hostname = ssh_details.hostname
        self.port = ssh_details.port
        self.username = ssh_details.username
        self.key_file = ssh_details.key_file
        self.local_dir = local_dir
        self.remote_dir = remote_dir
        self._ignore_paths = ignore_paths if ignore_paths is not None else []
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
        return self._rsync(path_from, path_to, rsync_opts)

    def down(self, path='', rsync_opts=None):
        if os.path.isabs(path):
            raise ValueError('path must be a relative path')
        remote = os.path.join(self.remote_dir, path)
        escaped_remote = sml.shell.quote(remote)
        local = os.path.join(self.local_dir, path)
        path_from = u'{}@{}:{}'.format(
            self.username, self.hostname, escaped_remote)
        path_to = local
        return self._rsync(path_from, path_to, rsync_opts)

    def list_remote(self, path='', rsync_opts=None):
        remote = os.path.join(self.remote_dir, path)
        escaped_remote = sml.shell.quote(remote)
        path = u'{}@{}:{}'.format(
            self.username, self.hostname, escaped_remote)
        return self._rsync_list(path, rsync_opts)

    def list_local(self, path='', rsync_opts=None):
        path = os.path.join(self.local_dir, path)
        return self._rsync_list(path, rsync_opts)

    def mkdir_remote(self, path):
        self._sftp.mkdir(os.path.join(self.remote_dir, path))

    def rmfile_remote(self, path):
        self._sftp.remove(os.path.join(self.remote_dir, path))

    def rmdir_remote(self, path):
        self._sftp.rmdir(os.path.join(self.remote_dir, path))

    def mvfile_remote(self, src_path, dest_path):
        self._sftp.rename(
            os.path.join(self.remote_dir, src_path),
            os.path.join(self.remote_dir, dest_path)
        )

    def _rsync(self, path_from, path_to, rsync_opts=None):
        rsync_opts = [] if rsync_opts is None else rsync_opts
        ssh_cmd = self._get_ssh_cmd()
        exclude_list = self._get_exclude_list()
        rsync_cmd = [
            'rsync', '-a', '-e', ssh_cmd, *exclude_list, *rsync_opts,
            path_from, path_to
        ]

        process = _run_ssh_cmd(rsync_cmd)
        return process

    def _rsync_list(self, path, rsync_opts=None):
        rsync_opts = [] if rsync_opts is None else rsync_opts
        ssh_cmd = self._get_ssh_cmd()
        exclude_list = self._get_exclude_list()
        rsync_cmd = [
            'rsync', '-a', '-e', ssh_cmd, '--itemize-changes', '--dry-run',
            '--out-format', '%n||%f||%M', *exclude_list, *rsync_opts, path,
            '/dev/false'
        ]
        process = _run_ssh_cmd(rsync_cmd)
        process_output = process.stdout.decode('utf-8')
        fs_objects = self._parse_rsync_list_result(process_output)
        return fs_objects

    def _get_ssh_cmd(self):
        ssh_options = ' '.join(SSH_OPTIONS)
        cmd = 'ssh {} -p {} -i {}'.format(
            ssh_options, self.port, self.key_file)
        return cmd

    def _get_exclude_list(self):
        exclude_list = []
        for _path in self._ignore_paths:
            exclude_list.extend(['--exclude', _path])
        return exclude_list

    def _parse_rsync_list_result(self, stdout):
        fs_objects = []
        for line in stdout.splitlines():
            path_with_trailing_slash, path, mtime_string = line.split('||')
            is_directory = path_with_trailing_slash != path
            mtime = datetime.strptime(mtime_string, '%Y/%m/%d-%H:%M:%S')
            if is_directory:
                fs_object = FsObject(
                    path_with_trailing_slash,
                    FsObjectType.DIRECTORY,
                    DirectoryAttrs(mtime)
                )
            else:
                fs_object = FsObject(
                    path_with_trailing_slash,
                    FsObjectType.FILE,
                    FileAttrs(mtime)
                )
            fs_objects.append(fs_object)
        return fs_objects


def _run_ssh_cmd(argv):
    """Run a command and print a message when a string is matched."""
    logging.info('Running command {}'.format(argv))
    start_time = time.time()
    process = subprocess.run(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    logging.info('Command took {:.2f} seconds to run'.format(
        time.time() - start_time))
    process.check_returncode()
    return process
