#!flask/bin/python
from flask import Flask, jsonify, request, render_template, redirect, url_for
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
options.disable_hardware_pulsing = True
options.gpio_slowdown = 3
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
        x = int(request.args.get('x'))
        y = int(request.args.get('y'))
        w = int(request.args.get('w'))
        h = int(request.args.get('h'))
    else:
        x = margin_left + (width + border_right) * column
        y = margin_top + (height + border_bottom) * row
        w = width
        h = height

    image = Image.open(filename)
    image.crop( (x, y, w, h) )
    # just in case it's bigger than 32x32
    image.thumbnail((32, 32), Image.ANTIALIAS)
    image = image.convert("RGB")
    offscreen_canvas.SetImage(image, unsafe=False)
    offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)

    return jsonify({'success': True, 'filename': filename, 'x': x, 'y': y, 'w': w, 'h': h})


@app.route('/pixie/api/v1.0/upload_image', methods=['POST'])
def upload_image():
    uploaded_file = request.files['file']
    filename = secure_filename(uploaded_file.filename)
    if filename != '':
        file_ext = os.path.splitext(filename)[1]
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
def index():
    return render_template('upload.html')


if __name__ == '__main__':
    app.run(debug=True)
