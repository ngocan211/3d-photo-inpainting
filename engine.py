import os
import logging
import subprocess
from queue import Queue
import time

from pipe_process import WhilePipeProcess
from s3_queue import queue_register, queue_connect
from multiprocessing import Pipe

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.ERROR)
QUEUE_CONFIG = {'address': ('0.0.0.0', 50001), 'authkey': b'abracadabrae'}


# cmd = "/home/ubuntu/anaconda3/envs/py37/bin/python -u /home/ubuntu/3d-photo-inpainting/main.py --srcfolder image2 > test.txt"
# subprocess.check_output([cmd], shell=True)

#
# # subprocess.Popen([cmd], close_fds=True)
# subprocess.Popen(['/home/ubuntu/anaconda3/envs/py37/bin/python' ,'/home/ubuntu/3d-photo-inpainting/main.py'], close_fds=True)
# # # subprocess.check_output([cmd], shell=True)
# # import os
# #
# # #
# # # os.system(cmd)
# # print('hello')
# import os, time, sys, subprocess
#
# if len(sys.argv) == 2:
#     time.sleep(1)
#     print('track end')
#     if sys.platform == 'darwin':
#         subprocess.Popen(['say', 'hello'])
# else:
#     log = open('somefile.txt', 'a')  # so that data written to it will be appended
#     print('main begin')
#     subprocess.Popen(['python', os.path.realpath(__file__), '0'], stdout=log, stderr=log, close_fds=True)
#     print('main end')

class FilePrepareProcess(WhilePipeProcess):
    def __init__(self, send_, api_queue_config, engine_pipe):
        self.region = 'ap-northeast-1'
        self.api_queue_config = api_queue_config
        self.engine_pipe = engine_pipe
        super().__init__('api_s3_queue_processor', None, send_)

    def target_function(self, pipe_):
        time.sleep(1)
        self.recv_ = queue_connect(self.api_queue_config)
        logging.error('Connected to API Queue')
        super().target_function(pipe_)

    def recv_while(self, append_list=None):
        return [self.recv_.get()]

    def handle_message(self, obj):
        uuid = obj['uuid']
        try:
            cmd = f'/home/ubuntu/anaconda3/envs/py37/bin/python -u /home/ubuntu/3d-photo-inpainting/main.py --srcfolder image_/{uuid} > {uuid}.txt'
            subprocess.check_output([cmd], shell=True)

            # s3_object = self.s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
            # obj['image_io'] = Image.open(io.BytesIO(s3_object['Body'].read()))

            self.send_.send(obj)
            # logging.error('sent pil')
        except Exception as ex:
            raise ex


if __name__ == '__main__':
    api_queue = Pipe()
    pipes_extract_to_engine = Pipe()

    FilePrepareProcess(
        send_=api_queue[0],
        api_queue_config=QUEUE_CONFIG,
        engine_pipe=pipes_extract_to_engine[0],
    ).start()

    queue = Queue()
    logging.error('API Queue serving..')
    queue_register(lambda: queue, config=None).get_server().serve_forever()
    logging.error('END SERVING')
