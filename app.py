from flask import Flask,request,jsonify
import json
from event import MessageReceiveEvent, UrlVerificationEvent, EventManager

app = Flask(__name__)

@app.route("/",methods = ['POST','GET'])
def hello_world():
    data = request.get_data()
    msg = json.loads(data)
    print(msg.get("challenge"))
    # print(json.dumps(msg["challenge"]))
    return jsonify({"challenge":msg.get("challenge")})

    # return "<p>Hello, World!</p>"

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=40500,debug=True)