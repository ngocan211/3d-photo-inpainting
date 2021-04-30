import os
import uuid
import urllib

from flask import Flask, request, render_template, jsonify

from engine import QUEUE_CONFIG
from s3_queue import queue_connect

app = Flask(__name__, static_folder='videos')

tagging_ = None


@app.route('/')
def index():
    return jsonify({'message': '3D photo'})


@app.route('/video-render', methods=['GET', 'POST'])
def video_render():
    uuid = urllib.parse.unquote(request.args.get('id', ''))
    with open(f'{uuid}.txt', 'r') as file:
        data = file.read()
        return data


_queue = None


@app.route('/video', methods=['GET', 'POST'])
def video():
    global _queue

    if _queue is None:
        _queue = queue_connect(QUEUE_CONFIG)
    try:
        url_link = urllib.parse.unquote(request.args.get('object_id', ''))
        if url_link:
            uuid_ = str(uuid.uuid4())
            folder = f'./image_/{uuid_}'
            os.makedirs(folder, exist_ok=True)
            fname = f'{folder}/{uuid_}{os.path.splitext(url_link)[1]}'
            urllib.request.urlretrieve(url_link, fname)
            _queue.put({'uuid': uuid_})
            return jsonify({'render': f'video-render?id={uuid_}', 'uuid': uuid_})
    except Exception as ex:
        print(ex)
        raise ex
        return jsonify({'error': 'Internal Error'})
    return render_template('upload.html')


if __name__ == "__main__":
    import sys

    port = (sys.argv[1:] + ["5000"])[0]
    app.run(host="0.0.0.0", port=int(port), debug=True, use_reloader=False)
