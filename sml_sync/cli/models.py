
import collections

Configuration = collections.namedtuple(
    'Configuration',
    ['project', 'server_id', 'local_dir', 'remote_dir', 'debug', 'ignore']
)
