# import the necessary packages
#from keras.preprocessing.image import img_to_array
from tensorflow.keras.preprocessing.image import img_to_array
from keras.applications import imagenet_utils
from redis_logger import log
from PIL import Image
import numpy as np
import settings
import helpers
import flask
import redis
import uuid
import time
import json
import io

# initialize our Flask application and Redis server
app = flask.Flask(__name__)
db = redis.StrictRedis(host=settings.REDIS_HOST,
	port=settings.REDIS_PORT, password=settings.REDIS_PASSWORD, db=settings.REDIS_DB)

def prepare_image(image, target):
	# if the image mode is not RGB, convert it
	if image.mode != "RGB":
		image = image.convert("RGB")

	# resize the input image and preprocess it
	image = image.resize(target)
	image = img_to_array(image)
	image = np.expand_dims(image, axis=0)
	image = imagenet_utils.preprocess_input(image)

	# return the processed image
	return image

@app.route("/")
def homepage():
	return "Welcome to the PyImageSearch Keras REST API!"

@app.route("/predict", methods=["POST"])
def predict():
	# initialize the data dictionary that will be returned from the
	# view
	data = {"success": False}

	# ensure an image was properly uploaded to our endpoint
	if flask.request.method == "POST":
		if flask.request.files.get("image"):
			# read the image in PIL format and prepare it for
			# classification
			image = flask.request.files["image"].read()
			image = Image.open(io.BytesIO(image))
			image = prepare_image(image,
				(settings.IMAGE_WIDTH, settings.IMAGE_HEIGHT))

			# ensure our NumPy array is C-contiguous as well,
			# otherwise we won't be able to serialize it
			image = image.copy(order="C")

			# generate an ID for the classification then add the
			# classification ID + image to the queue
			k = str(uuid.uuid4())
			image = helpers.base64_encode_image(image)
			d = {"id": k, "image": image}

			# subscribe to our result key BEFORE pushing the work, so the
			# notification can't fire before we're listening
			p = db.pubsub()
			p.subscribe(f"__keyspace@{settings.REDIS_DB}__:{k}")
			db.rpush(settings.IMAGE_QUEUE, json.dumps(d))
			log(f"queued {k}")

			# block until Redis tells us our key changed (no polling); the
			# first message is the subscribe confirmation, so skip it
			while True:
				message = p.get_message(timeout=30.0)
				if message is None or message["type"] == "message":
					break

			p.unsubscribe()
			p.close()

			# the notification carries no data, so fetch the result; this
			# also catches a result whose notification we missed
			output = db.get(k)
			if output is not None:
				data["predictions"] = json.loads(output.decode("utf-8"))
				db.delete(k)
				data["success"] = True
			
			log(f"done {k}" if data["success"] else f"timeout {k}")


	# return the data dictionary as a JSON response
	return flask.jsonify(data)

# for debugging purposes, it's helpful to start the Flask testing
# server (don't use this for production
if __name__ == "__main__":
	print("* Starting web service...")
	log("web server starting")
	app.run()
