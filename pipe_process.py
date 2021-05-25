import time
import logging
from multiprocessing import Process, Pipe

# logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.ERROR)


class PipeProcess:
    def __init__(self, name, recv_, send_):
        self.recv_ = recv_
        self.send_ = send_
        if not self.recv_ and not self.send_:
            self.pipes = Pipe()
            self.recv_ = self.pipes[0]
            self.send_ = self.pipes[1]
        self.process = Process(
            name=name,
            target=self.target_function,
            args=self.get_args_process()
        )

    def target_function(self, pipe_):
        pass

    def get_args_process(self):
        return (self.recv_,)

    def start(self):
        self.process.start()

    def start_and_join(self):
        self.process.start()
        self.process.join()


class WhilePipeProcess(PipeProcess):
    def recv_while(self, append_list=None):
        if not append_list:
            append_list = []
        pipe = self.recv_
        while pipe.poll():
            obj = pipe.recv()
            if not isinstance(obj, list):
                obj = [obj]
            for i in obj:
                append_list.append(i)
        return append_list

    def target_function(self, pipe_):
        while True:
            try:
                objs = self.recv_while()
                self.handle_messages(objs)
            except Exception as ex:
                error = '{}'.format(ex)
                if error == 'exit':
                    return
                logging.error('pos03 {}'.format(error))
            time.sleep(0.01)
        pass

    def handle_messages(self, objs):
        for obj in objs:
            if obj.get('exit', None):
                raise Exception('exit')
            self.handle_message(obj)


class ExtractProcess(WhilePipeProcess):
    def __init__(self, recv_, send_, handle_function=None):
        self.handle_function = handle_function
        super().__init__('feature extracting', recv_, send_)

    def target_function(self, pipe_):
        from vgg_extractor import VGGExtractor
        self.extractor = VGGExtractor()
        super().target_function(pipe_)

    def handle_message(self, obj):
        rs = self.handle_function(self.extractor, obj)
        if self.send_:
            self.send_.send(rs)
