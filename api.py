import os
import uuid
import urllib

import yaml
from flask import Flask, request, render_template, jsonify
from engine import QUEUE_CONFIG
from s3_queue import queue_connect

app = Flask(__name__, static_folder='videos')
config = yaml.load(open('argument.yml', 'r'))
_queue = None


@app.route('/')
def index():
    return jsonify({'message': '3D photo'})


@app.route('/video', methods=['GET', 'POST'])
def video():
    return render_template('upload.html')


@app.route('/video_model', methods=['GET', 'POST'])
def video_model():
    global _queue

    if _queue is None:
        _queue = queue_connect(QUEUE_CONFIG)
    try:
        url_link = urllib.parse.unquote(request.args.get('object_id', ''))
        if url_link:
            uuid_ = str(uuid.uuid4())
            folder = f'./image'
            # os.makedirs(folder, exist_ok=True)
            save_file = f'{folder}/{uuid_}.jpg'
            urllib.request.urlretrieve(url_link, save_file)  # save image url to file
            _queue.put({'uuid': uuid_})
            return jsonify({'uuid': uuid_, 'message': 'create 3D model '})
    except Exception as ex:
        print(ex)
        raise ex
        return jsonify({'error': 'Internal Error'})
    return jsonify({'message': 'create model'})


@app.route('/video_gen', methods=['GET', 'POST'])
def video_gen():
    global _queue
    global config

    if _queue is None:
        _queue = queue_connect(QUEUE_CONFIG)

    try:
        uuid_ = urllib.parse.unquote(request.args.get('uuid', ''))
        type_id = urllib.parse.unquote(request.args.get('type_id', None))
        if uuid_ and type_id:
            video_file = config['video_folder'] + '/' + uuid_ + '_' + config['video_postfix'][int(type_id)] + '.mp4'
            video_file_in_process = video_file + '.in_process'
            ply_file = config['mesh_folder'] + '/' + uuid_ + '.ply'

            if os.path.isfile(video_file):
                return jsonify({'uuid': uuid_, 'video': video_file})

            if os.path.isfile(video_file_in_process):
                return jsonify({'uuid': uuid_, 'message': 'wait for video in generating'})

            if os.path.isfile(ply_file):
                _queue.put({'uuid': uuid_, 'type_id': type_id})
                return jsonify({'uuid': uuid_, 'message': 'start to gen video'})

            return jsonify({'uuid': uuid_, 'message': 'wait for model file'})

        return jsonify({'uuid': uuid_, 'message': 'nothing doing'})

    except Exception as ex:
        print(ex)
        raise ex
        return jsonify({'error': 'Internal Error'})

    return jsonify({'message': 'video gen'})


@app.route('/video_log', methods=['GET', 'POST'])
def video_log():
    uuid = urllib.parse.unquote(request.args.get('id', ''))
    with open(f'video_log/{uuid}.txt', 'r') as file:
        data = file.read()
        return data


if __name__ == "__main__":
    import sys

    port = (sys.argv[1:] + ["5000"])[0]
    app.run(host="0.0.0.0", port=int(port), debug=True, use_reloader=False)
