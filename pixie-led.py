#!flask/bin/python
from flask import Flask, jsonify, request, render_template, redirect, url_for, abort
from werkzeug.utils import secure_filename
import sys
import time
import os

from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image


app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # max 10MB
app.config['UPLOAD_EXTENSIONS'] = ['.jpg', '.png', '.gif']
app.config['UPLOAD_PATH'] = '/home/ubuntu/pixie/cache'


# prevent connection being reset during file upload ?
# from : https://www.cocept.io/blog/development/flask-file-upload-connection-reset/
# from werkzeug.wsgi import LimitedStream
# class StreamConsumingMiddleware(object):

#     def __init__(self, app):
#         self.app = app

#     def __call__(self, environ, start_response):
#         stream = LimitedStream(environ['wsgi.input'],
#                                int(environ['CONTENT_LENGTH'] or 0))
#         environ['wsgi.input'] = stream
#         app_iter = self.app(environ, start_response)
#         try:
#             stream.exhaust()
#             for event in app_iter:
#                 yield event
#         finally:
#             if hasattr(app_iter, 'close'):
#                 app_iter.close()
# app.wsgi_app = StreamConsumingMiddleware(app.wsgi_app)


# Configuration for the matrix
options = RGBMatrixOptions()
options.rows = 32
options.cols = 32
options.chain_length = 1
options.parallel = 1
options.hardware_mapping = 'adafruit-hat'
options.disable_hardware_pulsing = False  # default: False
options.pwm_bits = 8  # default: 11
options.pwm_lsb_nanoseconds = 200  # default: 130
options.gpio_slowdown = 3  # default: 2
options.drop_privileges = False

matrix = RGBMatrix(options=options)
offscreen_canvas = matrix.CreateFrameCanvas()

# @app.route('')

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
    # bad default?
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
    # just in case it's bigger than 32x32
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
        # Permission denied if you don't close the file?
        uploaded_file.close()
    # return jsonify({"succes": True})
    # don't do this to allow multiple?
    return redirect('/pixie/api/v1.0/show_image?filename=cache/'+filename)


# WWW Routes
@app.route('/pixie/upload', methods=['GET', 'POST'])
def upload():
    return render_template('upload.html')


@app.route('/pixie/list', method=['GET'])
def show_list():
    return render_template('list.html', files=['a', 'b', 'c'])


@app.route('/pixie/queue', method=['GET'])
def show_queue():
    return render_template('queue.html')


if __name__ == '__main__':
    app.run(debug=True)
