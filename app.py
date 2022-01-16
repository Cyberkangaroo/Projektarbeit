from flask import Flask

app = Flask("test")

@app.route("/")
def hello_world():
    return "<p>test!</p>"