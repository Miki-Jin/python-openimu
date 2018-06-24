import tornado.websocket
import tornado.ioloop
import tornado.httpserver
import tornado.web
import json
import time
import math
import os
from openimu import OpenIMU

server_version = '1.0 Beta'

callback_rate = 50

class WSHandler(tornado.websocket.WebSocketHandler):
        
    def open(self):
        self.callback = tornado.ioloop.PeriodicCallback(self.send_data, callback_rate)
        self.callback.start()
        
    def send_data(self):
        if not imu.paused:
            d = imu.get_latest()
            self.write_message(json.dumps({ 'messageType' : 'event',  'data' : { 'newOutput' : d }}))
        else:
            return False

    def on_message(self, message):
        global imu
        message = json.loads(message)
        # Except for a few exceptions stop the automatic message transmission if a message is received
        if message['messageType'] != 'serverStatus' and list(message['data'].keys())[0] != 'startLog' and list(message['data'].keys())[0] != 'stopLog':
            self.callback.stop()
            imu.pause()
        if message['messageType'] == 'serverStatus':
            if imu.logging:
                fileName = imu.logger.user['fileName']
            else:
                fileName = ''
            self.write_message(json.dumps({ 'messageType' : 'serverStatus', 'data' : { 'serverVersion' : server_version, 'serverUpdateRate' : callback_rate,  'packetType' : imu.packet_type,
                                                                                        'deviceProperties' : imu.imu_properties, 'deviceId' : imu.device_id, 'logging' : imu.logging, 'fileName' : fileName }}))
        elif message['messageType'] == 'requestAction':
            if list(message['data'].keys())[0] == 'gA':
                print('requesting')
                data = imu.openimu_get_all_param()
                print(data)
                self.write_message(json.dumps({ "messageType" : "requestAction", "data" : { "gA" : data }}))
            elif list(message['data'].keys())[0] == 'uP':
                data = imu.openimu_update_param(message['data']['uP']['paramId'], message['data']['uP']['value'])
                self.write_message(json.dumps({ "messageType" : "requestAction", "data" : { "uP" : data }}))
            elif list(message['data'].keys())[0] == 'sC':
                imu.openimu_save_config()
                self.write_message(json.dumps({ "messageType" : "requestAction", "data" : { "sC" : {} }}))
            elif list(message['data'].keys())[0] == 'startStream':
                imu.connect()
                self.callback.start()  
            elif list(message['data'].keys())[0] == 'stopStream':
                imu.pause()
            elif list(message['data'].keys())[0] == 'startLog' and imu.logging == 0: 
                data = message['data']['startLog']
                imu.start_log(data) 
                self.write_message(json.dumps({ "messageType" : "requestAction", "data" : { "logfile" : imu.logger.name }}))
            elif list(message['data'].keys())[0] == 'stopLog' and imu.logging == 1: 
                imu.stop_log()                
                self.write_message(json.dumps({ "messageType" : "requestAction", "data" : { "logfile" : '' }}))
        elif  0 and message['messageType'] == 'requestAction':
            if list(message['data'].keys())[0] == 'startStream':
                imu.restore_odr()
                self.callback.start()  
            elif list(message['data'].keys())[0] == 'stopStream':
                imu.set_quiet()
            elif list(message['data'].keys())[0] == 'startLog' and imu.logging == 0: 
                data = message['data']['startLog']
                imu.start_log(data) 
                self.write_message(json.dumps({ "messageType" : "requestAction", "data" : { "logfile" : imu.logger.name }}))
            elif list(message['data'].keys())[0] == 'stopLog' and imu.logging == 1: 
                imu.stop_log()                
                self.write_message(json.dumps({ "messageType" : "requestAction", "data" : { "logfile" : '' }}))
            elif list(message['data'].keys())[0] == 'listFiles':
                logfiles = [f for f in os.listdir('data') if os.path.isfile(os.path.join('data', f)) and f.endswith(".csv")]
                self.write_message(json.dumps({ "messageType" : "requestAction", "data" : { "listFiles" : logfiles }}))
            elif list(message['data'].keys())[0] == 'loadFile':
                print(message['data']['loadFile']['graph_id'])
                f = open("data/" + message['data']['loadFile']['graph_id'],"r")
                self.write_message(json.dumps({ "messageType" : "requestAction", "data" : { "loadFile" :  f.read() }}))


    def on_close(self):
        self.callback.stop()
        return False

    def check_origin(self, origin):
        return True
 
if __name__ == "__main__":
    # Create IMU
    imu = OpenIMU(ws=True)
    imu.find_device()    
    # Set up Websocket server on Port 8000
    # Port can be changed
    application = tornado.web.Application([(r'/', WSHandler)])
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8000)
    tornado.ioloop.IOLoop.instance().start()
    