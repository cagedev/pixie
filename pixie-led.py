#!flask/bin/python
from flask import Flask, jsonify, request
import sys, time
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image


app = Flask(__name__)

# Configuration for the matrix
options = RGBMatrixOptions()
options.rows = 32
options.cols = 32
options.chain_length = 1
options.parallel = 1
options.hardware_mapping = 'adafruit-hat'

matrix = RGBMatrix(options = options)
offscreen_canvas = matrix.CreateFrameCanvas()

#@app.route('')

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


if __name__ == '__main__':
    app.run(debug=True)
