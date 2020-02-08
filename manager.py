#!/usr/bin/python3
import os
import time
import systemd.daemon
import paho.mqtt.client as mqtt
from sysdmanager import SystemdManager
import json
import uuid

config = dict() 
client = mqtt.Client()
lastPoll = time.time() - 20 
client_id = 'pysystemd-to-mqtt/' + str(uuid.uuid4())

def sendDiscovery(service):
    global config
    topic = "%s/switch/%s/%s/config" % (
            config['hass']['autodiscoveryTopic'],
            config['alias'],
            service)
    stateTopic = "%s/%s/%s/state" % (config['basetopic'],config['alias'],service)
    commandTopic = "%s/%s/%s/set" % (config['basetopic'],config['alias'],service)

    payload = {
            "name": service,
            "state_topic": stateTopic,
            "command_topic": commandTopic,
            "unique_id":"%s_%s" % (config['alias'],service),
            "device":{
                "identifiers": config['alias'],
                "name": config['alias'],
                "sw_version":"pysystemd-manager-mqtt",
                "model":"Aesome",
                "manufacturer":"NURDs"
                }
            }
    return topic, json.dumps(payload)

def on_connect(client, userdata, flags, rc):
    global config
    print("Connected with result code "+str(rc))
    for service in config['services']:
        service = service.replace('.','_')
        commandTopic = "%s/%s/%s/set" % (config['basetopic'],config['alias'],service)
        if config['hass']['autodiscovery'] == 1:
            payload = sendDiscovery(service)
            client.publish(payload[0], payload=payload[1], retain=True)
        client.subscribe(commandTopic)

def on_message(client, userdata, msg):
    global config
    service = msg.topic.split('/')[-2].replace('_','.')
    if msg.payload == b"ON":
        print("Starting %s" % service)
        manager.start_unit(service)
        state = True 
    if msg.payload == b"OFF":
        print("Stopping %s" % service)
        manager.stop_unit(service)
        state = False 
    topic = "%s/%s/%s/state" % (config['basetopic'],config['alias'],service)
    txtState = "ON" if state else "OFF"
    client.publish(topic, txtState)

if __name__ == '__main__':
    print('Starting up ...')
    with open('%s/config.json' % os.path.dirname(os.path.abspath(__file__)), 'r') as myfile:
        data=myfile.read()
        config = json.loads(data)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(config['mqtt']['host'], config['mqtt']['port'], 60)
    manager = SystemdManager()
    systemd.daemon.notify('READY=1')
    while True:
        now = time.time()
        if (now - lastPoll) > 10:
            for service in config['services']:
                state = manager.is_active(service)
                service = service.replace('.','_')
                topic = "%s/%s/%s/state" % (config['basetopic'],config['alias'],service)
                txtState = "ON" if state else "OFF"
                client.publish(topic, txtState)
            lastPoll = now
        client.loop(timeout=0.1, max_packets=1)
