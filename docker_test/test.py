from time import sleep
from flask import Flask
#from waitress import serve


app = Flask(__name__)
@app.route("/")
def test():
    print("started")
    for i in range(600):
        print("iteration : ", i)
        sleep(1)
    print("finished")
    return i


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
