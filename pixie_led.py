#!flask/bin/python
from flask import Flask, jsonify, request, render_template, redirect, url_for, abort
from werkzeug.utils import secure_filename
import sys
import time
import os
import redis
from rq import Queue
import rq_dashboard

from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image


# Config for Flask
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # max 10MB
app.config['UPLOAD_EXTENSIONS'] = ['.jpg', '.png', '.gif']
app.config['UPLOAD_PATH'] = '/root/pixie/cache'
app.config['IMAGE_FILE_DIRS'] = ['img', 'cache']

# Config for Redis
r = redis.Redis()
q = Queue(connection=r)
app.config.from_object(rq_dashboard.default_settings)
app.register_blueprint(rq_dashboard.blueprint, url_prefix="/pixie/admin/rq")

# Config for RGBMatrix
options = RGBMatrixOptions()
options.rows = 32
options.cols = 32
options.chain_length = 1
options.parallel = 1
options.hardware_mapping = 'adafruit-hat-pwm'
options.disable_hardware_pulsing = False  # default: False
options.pwm_bits = 6  # default: 11
options.pwm_lsb_nanoseconds = 300  # default: 130; 50 blocks in workers?
options.gpio_slowdown = 1  # default: 1
options.drop_privileges = False

matrix = RGBMatrix(options=options)
offscreen_canvas = matrix.CreateFrameCanvas()


# API Routes
@app.route('/pixie/api/v1.0/fill', methods=['GET'])
def set_color():
    global offscreen_canvas, matrix
    r = int(request.args.get('r', 100)) % 255
    g = int(request.args.get('g', 0)) % 255
    b = int(request.args.get('b', 0)) % 255
    offscreen_canvas.Clear()
    offscreen_canvas.Fill(r, g, b)
    offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)
    return jsonify({"success": True, 'r': r, 'g': g, 'b': b})


@app.route('/pixie/api/v1.0/enqueue_gif', methods=['GET'])
def enqueue_gif():
    if request.args.get('filename'):
        job = q.enqueue(panel_gif, request.args.get('filename'))
        return f"{job.enqueued_at}: job {job.id} added to queue. {len(q)} tasks in queue."
    else:
        return f"{len(q)} tasks in queue."


@app.route('/pixie/api/v1.0/show_gif', methods=['GET'])
def show_gif():
    filename = request.args.get('filename', './img/blank.png')
    loop = int(request.args.get('loop', '10'))
    delay = float(request.args.get('delay', '0.2'))
    panel_gif(filename, loop=loop, delay=delay)
    return jsonify({'success': True, 'image_file': filename})


@app.route('/pixie/api/v1.0/show_image', methods=['GET'])
def show_image():
    global matrix, offscreen_canvas
    image_file = request.args.get('filename', './img/blank.png')
    image = Image.open(image_file)
    image.thumbnail((32, 32), Image.ANTIALIAS)
    image = image.convert("RGB")
    offscreen_canvas.SetImage(image, unsafe=False)
    offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)
    return jsonify({'success': True, 'image_file': image_file})


@app.route('/pixie/api/v1.0/show_sprite', methods=['GET'])
def show_sprite():
    global matrix, offscreen_canvas

    # filename, margin-top, margin-left, padding-top, padding-left, column, row,
    filename = request.args.get('filename', default='./cache/sf-portraits.png')

    margin_top = int(request.args.get('margin-top', default=1))
    margin_left = int(request.args.get('margin-left', default=0))
    border_bottom = int(request.args.get('border-bottom', default=5))
    border_right = int(request.args.get('border-right', default=5))
    width = int(request.args.get('width', default=48))  # should be 32?
    height = int(request.args.get('height', default=64))  # should be 32?

    column = int(request.args.get('column', default=0))
    row = int(request.args.get('row', default=0))

    # filename, x, y, w, h
    if 'x' in request.args and 'y' in request.args and 'w' in request.args and 'h' in request.args:
        x1 = int(request.args.get('x'))
        y1 = int(request.args.get('y'))
        x2 = int(request.args.get('w')) + x1
        y2 = int(request.args.get('h')) + y1
    else:
        x1 = margin_left + (width + border_right) * column
        y1 = margin_top + (height + border_bottom) * row
        x2 = x1 + width
        y2 = y1 + height

    image = Image.open(filename)
    cropped_image = image.crop((x1, y1, x2, y2))
    cropped_image.thumbnail((32, 32), Image.ANTIALIAS)
    cropped_image = cropped_image.convert("RGB")
    offscreen_canvas.SetImage(cropped_image, unsafe=False)
    offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)

    return jsonify({'success': True, 'filename': filename, 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2})


@app.route('/pixie/api/v1.0/upload_image', methods=['POST'])
def upload_image():
    uploaded_file = request.files['file']
    filename = secure_filename(uploaded_file.filename)
    if filename != '':
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in app.config['UPLOAD_EXTENSIONS']:
            abort(400)
        uploaded_file.save(os.path.join(app.config['UPLOAD_PATH'], filename))
        uploaded_file.close()
        if file_ext.lower() == '.gif':
            return redirect('/pixie/api/v1.0/show_gif?filename=cache/'+filename)
        else:
            return redirect('/pixie/api/v1.0/show_image?filename=cache/'+filename)
    else:
        return url_for('upload')


# WWW Routes
@app.route('/pixie/upload', methods=['GET', 'POST'])
def upload():
    return render_template('upload.html')


@app.route('/pixie/list', methods=['GET'])
def show_list():
    files = []
    for directory in app.config['IMAGE_FILE_DIRS']:
        files.extend([os.path.join(directory, file)
                      for file in os.listdir(directory)])
    return render_template('list.html', files=files)


@app.route('/pixie/queue', methods=['GET'])
def show_queue():
    if request.args.get('n'):
        job = q.enqueue(fake_task, int(request.args.get('n')))
        return f"{job.enqueued_at}: job {job.id} added to queue. {len(q)} tasks in queue."
    else:
        return f"{len(q)} tasks in queue."
    # return render_template('queue.html')


# Task functions
def fake_task(n):
    print(f"Task started. Delaying {n} seconds")
    time.sleep(n)
    print("Complete")
    return n


def panel_gif(filename, loop=10, delay=0.2):
    # os.system("sudo /home/ubuntu/rpi-rgb-led-matrix/utils/led-image-viewer /home/ubuntu/pixie/cache/temp3.gif -t 5")
    global matrix, offscreen_canvas
    image = Image.open(filename)
    for l in range(loop):
        for frame in range(0, image.n_frames):
            image.seek(frame)
            offscreen_canvas.SetImage(image.convert('RGB'), unsafe=False)
            offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)
            matrix.SetImage(image.convert('RGB'))
            time.sleep(delay)


if __name__ == '__main__':
    app.run(debug=True)
