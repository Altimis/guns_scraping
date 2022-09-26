from time import sleep
from flask import Flask
#from waitress import serve
import os


app = Flask(__name__)


@app.route("/")
def main():
    for i in range(10):
        print(i)
    return "Done!"


if __name__ == "__main__":
    #test()
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
