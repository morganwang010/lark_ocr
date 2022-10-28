#!/usr/bin/env python3.8

import os,json,base64,threading
import logging
import requests
from api import MessageApiClient
from event import MessageReceiveEvent, UrlVerificationEvent, EventManager
from flask import Flask, jsonify
from dotenv import load_dotenv, find_dotenv
from datetime import datetime 
from PIL import Image
from io import BytesIO

# load env parameters form file named .env
load_dotenv(find_dotenv())

app = Flask(__name__)

# load from env
APP_ID = os.getenv("APP_ID")
APP_SECRET = os.getenv("APP_SECRET")
VERIFICATION_TOKEN = os.getenv("VERIFICATION_TOKEN")
ENCRYPT_KEY = os.getenv("ENCRYPT_KEY")
LARK_HOST = os.getenv("LARK_HOST")
TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
MESSAGE_IMG_URL = "https://open.feishu.cn/open-apis/im/v1/messages/"
IMG_REC_URL = "https://open.feishu.cn/open-apis/optical_char_recognition/v1/image/basic_recognize"
TokenTime = {}
token_data = json.dumps({"app_id": APP_ID,"app_secret":APP_SECRET})
TOKEN = ""
# init service
message_api_client = MessageApiClient(APP_ID, APP_SECRET, LARK_HOST)
event_manager = EventManager()


@event_manager.register("url_verification")
def request_url_verify_handler(req_data: UrlVerificationEvent):
    # url verification, just need return challenge
    if req_data.event.token != VERIFICATION_TOKEN:
        raise Exception("VERIFICATION_TOKEN is invalid")
    return jsonify({"challenge": req_data.event.challenge})

def img_rec(IMG_REC_URL,rec_headers,rec_data,sender_id):
    rec_res = requests.post(IMG_REC_URL,headers=rec_headers,data=rec_data)
    txt_list = json.loads(rec_res.content).get("data").get("text_list")
    s = ""
    for txt in txt_list:
        s = s + str(txt)
    print(s)
    open_id = sender_id.open_id
    text_content = json.dumps({"text":s})
    # echo text message
    message_api_client.send_text_with_open_id(open_id, text_content)
def msg():
    return jsonify()

@event_manager.register("im.message.receive_v1")
def message_receive_event_handler(req_data: MessageReceiveEvent):
    sender_id = req_data.event.sender.sender_id
    message = req_data.event.message
    # print(get_exp_seconds())
    if message.message_type == "image":
        teant_token = get_exp_seconds()
        m_id = message.message_id
        url = MESSAGE_IMG_URL + m_id + "/resources/" + json.loads(message.content).get("image_key") + "?type=image"
        headers = {"Authorization": "Bearer " + teant_token}
        res = requests.get(url,headers=headers)
        img = Image.open(BytesIO(res.content))
        img_b64 = base64.b64encode(BytesIO(res.content).read())
        # print((img_b64.decode("utf-8") ))
        rec_headers = {"Authorization":"Bearer " + teant_token }
        rec_data = json.dumps({"image":img_b64.decode("utf-8") })
        try:
            t1 = threading.Thread(img_rec(IMG_REC_URL,rec_headers,rec_data,sender_id))
            t2 = threading.Thread(msg())
            t1.start()
            t2.start()
        except:
            return jsonify()

        # print(json.loads(rec_res.content).get("data").get("text_list"))
        # print(json.loads(message.content).get("image_key"))
        logging.warn("Other types of messages have not been processed yet")
        return jsonify()
        # get open_id and text_content
    open_id = sender_id.open_id
    text_content = message.content
    print(text_content)
    # echo text message
    message_api_client.send_text_with_open_id(open_id, text_content)
    return jsonify()

def get_exp_seconds():
    if(len(TokenTime) == 0):
        a = datetime.now()
        TokenTime["now"] = a
        b = requests.post(TOKEN_URL,data=token_data)
        r = json.loads(b.text)
        TokenTime["token"] = datetime.now()
        TokenTime["exp"] = r.get("expire")
        TokenTime["TrueToken"] = r.get("tenant_access_token")

    else:
        TokenTime["now"] = datetime.now()
        if(( TokenTime["now"] - TokenTime["token"]).seconds > TokenTime["exp"]):
            a = datetime.now()
            TokenTime["now"] = a
            b = requests.post(TOKEN_URL,data=token_data)
            r = json.loads(b.text)
            TokenTime["token"] = datetime.now()
            TokenTime["exp"] = r.get("expire")
            TokenTime["TrueToken"] = r.get("tenant_access_token")

    return TokenTime["TrueToken"]


@app.errorhandler
def msg_error_handler(ex):
    logging.error(ex)
    response = jsonify(message=str(ex))
    response.status_code = (
        ex.response.status_code if isinstance(ex, requests.HTTPError) else 500
    )
    return response


@app.route("/", methods=["POST"])
def callback_event_handler():
    # init callback instance and handle
    event_handler, event = event_manager.get_handler_with_event(VERIFICATION_TOKEN, ENCRYPT_KEY)

    return event_handler(event)


if __name__ == "__main__":
    # init()
    app.run(host="0.0.0.0", port=40500, debug=True)
