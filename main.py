pycryptodome==3.14.1
google-cloud-pubsub==2.9.0
import sys
import base64
from Crypto.Cipher import AES
from google.cloud import pubsub_v1
import json
from datetime import datetime, timezone

BS = 16
pad = lambda s: bytes(s + (BS - len(s) % BS) * chr(BS - len(s) % BS), 'utf-8')
unpad = lambda s : s[0:-ord(s[-1:])]
project_id = 'crm-production-335312'
table_name = ''
topic_sink = ''
encrypted_cols = []
date_cols = []
publisher = pubsub_v1.PublisherClient()

def hello_pubsub(event, context):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """

    payload = base64.b64decode(event['data']).decode('utf-8')
    data = json.loads(payload)
    globals()['table_name'] = data['table_name']
    globals()['encrypted_cols'] = data['encrypted_cols']
    globals()['date_cols'] = data['date_cols']
    globals()['topic_sink'] = 'decrypt-%s-sink' %table_name

    for col in date_cols:
        if data[col] is not None:
            data[col] = str(data[col])
    for col in encrypted_cols:
        decrypted_data = udf_decrypt(data[col])
        data['%s_decrypted' %col] = decrypted_data
    data.pop('table_name')
    data.pop('encrypted_cols')
    data.pop('date_cols')
    print('data: %s' % data)
    json_data = {
        "topic": topic_sink,
        "message": {
            "table_name": table_name,
            data['id']: data
        }
    }
    publish(json_data)

# Publishes a message to a Cloud Pub/Sub topic.
def publish(data):
    topic_name = data.get("topic")
    message = data.get("message")
    print('topic_name: %s, message: %s' %(topic_name, message))

    if not topic_name or not message:
        return ('Missing "topic" and/or "message" parameter.', 400)

    print(f'Publishing message to topic {topic_name}')

    # References an existing topic
    topic_path = publisher.topic_path(project_id, topic_name)

    message_json = json.dumps({
        'data': {'message': message},
    })
    message_bytes = message_json.encode('utf-8')

    # Publishes a message
    try:
        publish_future = publisher.publish(topic_path, data=message_bytes)
        publish_future.result()  # Verify the publish succeeded
        return 'Message published.'
    except Exception as e:
        print(e)
        return (e, 500)

class AESCipher:

    def __init__( self, key ):
        self.key = bytes(key, 'utf-8')

    def encrypt( self, raw ):
        if raw is None:
            raw = "Unknown"
        if len(str(raw)) == 0 or raw is None:
            raw = "Unknown"
        iv = "encryptionIntVec".encode('utf-8')
        cipher = AES.new(self.key, AES.MODE_CFB, iv )
        raw = pad(raw)  
        return base64.b64encode(cipher.encrypt(raw)).decode('utf-8')
    def decrypt( self, enc ):
        try:
            iv = "encryptionIntVec".encode('utf-8')
            enc = base64.b64decode(enc)
            cipher = AES.new(self.key, AES.MODE_CFB, iv )
            return unpad(cipher.decrypt( enc )).decode('utf8')
        except:
            return enc

def udf_decrypt(source):
    aes = AESCipher('enIntVecTest2021')
    decVal = aes.decrypt(source)
    result = customValidation(decVal,source)
    return result
# cipher = AESCipher('enIntVecTest2021')

def checkParsing(val,initial):
    try:
        json.dumps(val)
        return val
    except:
        return initial

def customValidation(val,initial):
    if val=="":
        return initial
    try:
        json.dumps(val)
        return val
    except:
        return initial