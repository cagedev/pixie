from rgbmatrix import RGBMatrix, RGBMatrixOptions
from PIL import Image


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

image_file = 'cache/temp2.gif'



def panel_gif(filename, loop=1, delay=1):
    global matrix, offscreen_canvas
    image = Image.open(filename)
    for l in range(loop):
        for frame in range(0, image.n_frames):
        print(image.n_frames)
        image.seek(frame)
        offscreen_canvas.SetImage(image.convert('RGB'), unsafe=False)
        offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)
        matrix.SetImage(image.convert('RGB'))
        time.sleep(delay)


image = Image.open(filename)
cropped_image = image.crop((x1, y1, x2, y2))
cropped_image.thumbnail((32, 32), Image.ANTIALIAS)
cropped_image = cropped_image.convert("RGB")
offscreen_canvas.SetImage(cropped_image, unsafe=False)
offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)