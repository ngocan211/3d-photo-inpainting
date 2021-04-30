from queue import Queue
from multiprocessing.managers import BaseManager


class QueueManager(BaseManager):
    pass


def queue_register(callable=None, config=None):
    if config is None:
        config = {'address': ('0.0.0.0', 50001), 'authkey': b'abracadabrae'}
    QueueManager.register('get_queue', callable=callable)
    # logging.error('Queue at {}'.format(config))
    return QueueManager(address=config['address'], authkey=config['authkey'])


def queue_connect(config=None):
    m = queue_register(config=config)
    m.connect()
    # logging.error('S3 queue processor connected')
    return m.get_queue()


if __name__ == '__main__':
    queue = Queue()
    print('S3 Queue serving..')
    queue_register(lambda: queue).get_server().serve_forever()
    print('END SERVING')
