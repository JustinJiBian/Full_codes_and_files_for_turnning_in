import time
import socket
import select
import sys
import string
import indexer_student
import json
import pickle as pkl
from chat_utils import *
import chat_group_student as grp
from tensorflow import keras
import threading
import hashlib
import base64
from io import BytesIO
from PIL import Image
import numpy as np

class NeuralNetworks:
    def __init__(self):
        # here we load our hand-writen digit recognition neural network models
        sml = keras.layers.TFSMLayer('mnist_cnn', call_endpoint='serve')
        self.cnn_model_v1 = keras.Sequential([keras.Input((28, 28, 1)), sml])

        sml2 = keras.layers.TFSMLayer('mnist_cnn_v2', call_endpoint='serve')
        self.cnn_model_v2 = keras.Sequential([keras.Input((28, 28, 1)), sml2])

        sml3 = keras.layers.TFSMLayer('mnist_cnn_v3', call_endpoint='serve')
        self.cnn_model_v3 = keras.Sequential([keras.Input((28, 28, 1)), sml3])

class Server:
    def __init__(self):
        self.new_clients = []              # sockets of new (not yet logged-in) clients
        self.logged_name2sock = {}         # username -> socket
        self.logged_sock2name = {}         # socket -> username
        self.all_sockets = []
        self.group = grp.Group()
        # start server
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(SERVER)
        self.server.listen(5)
        self.all_sockets.append(self.server)
        # initialize past chat indices
        self.indices = {}
        # sonnet indexer
        self.sonnet = indexer_student.PIndex("AllSonnets.txt")

        self.users = None             # placeholder for the future register info part
        self.clients = {}             # empty dictionary for clients

        sml = keras.layers.TFSMLayer('mnist_cnn', call_endpoint='serve')
        self.cnn_model_v1 = keras.Sequential([keras.Input((28, 28, 1)), sml])

        sml2 = keras.layers.TFSMLayer('mnist_cnn_v2', call_endpoint='serve')
        self.cnn_model_v2 = keras.Sequential([keras.Input((28, 28, 1)), sml2])

        sml3 = keras.layers.TFSMLayer('mnist_cnn_v3', call_endpoint='serve')
        self.cnn_model_v3 = keras.Sequential([keras.Input((28, 28, 1)), sml3])

    def new_client(self, sock):
        # add new client socket to lists for select
        print('new client...')
        sock.setblocking(0)
        self.new_clients.append(sock)
        self.all_sockets.append(sock)

    def login(self, sock):
        # read the login message from a new client
        try:
            msg = json.loads(myrecv(sock))
            if len(msg) > 0:
                if msg["action"] == "login":
                    name = msg["name"]
                    if self.group.is_member(name) != True:
                        # move socket from new clients list to logged clients
                        self.new_clients.remove(sock)
                        self.logged_name2sock[name] = sock
                        self.logged_sock2name[sock] = name
                        # load chat history of that user
                        if name not in self.indices.keys():
                            try:
                                self.indices[name] = pkl.load(open(name + '.idx', 'rb'))
                            except IOError:  # chat index does not exist, then create one
                                self.indices[name] = indexer_student.Index(name)
                        print(name + ' logged in')
                        self.group.join(name)
                        mysend(sock, json.dumps({"action": "login", "status": "ok"}))
                    else:
                        # duplicate login attempt
                        mysend(sock, json.dumps({"action": "login", "status": "duplicate"}))
                        print(name + ' duplicate login attempt')
                else:
                    print('wrong code received')
            else:
                # client died unexpectedly during login
                self.logout(sock)
        except:
            # On exception (e.g., broken socket), clean up
            # CHANGED: also remove sock from new_clients and all_sockets, then close it
            if sock in self.new_clients:
                self.new_clients.remove(sock)
            if sock in self.all_sockets:
                self.all_sockets.remove(sock)
            sock.close()

    def logout(self, sock):
        # remove sock from all lists and save state
        name = self.logged_sock2name[sock]
        pkl.dump(self.indices[name], open(name + '.idx', 'wb'))
        del self.indices[name]
        del self.logged_name2sock[name]
        del self.logged_sock2name[sock]
        self.all_sockets.remove(sock)
        self.group.leave(name)
        sock.close()


    def handle_msg(self, client):
        msg = myrecv(client)

        print("SERVER ←", repr(msg))
        if not msg:
            return

        data = json.loads(msg)
        print("SERVER parsed data keys:", list(data.keys()), "action:", data.get("action"))

        try:
            with open('users.json', 'r') as f:
                self.users = json.load(f)
        except FileNotFoundError:
            self.users = {}
        if len(msg) > 0:
            msg = json.loads(msg)
            if msg["action"] == "connect":
                # handle connect request
                to_name = msg["target"]
                from_name = self.logged_sock2name[client]
                if to_name == from_name:
                    msg = json.dumps({"action": "connect", "status": "self"})
                elif self.group.is_member(to_name):
                    to_sock = self.logged_name2sock[to_name]
                    self.group.connect(from_name, to_name)
                    the_guys = self.group.list_me(from_name)
                    msg = json.dumps({"action": "connect", "status": "success"})
                    for g in the_guys[1:]:
                        to_sock = self.logged_name2sock[g]
                        mysend(to_sock, json.dumps({
                            "action": "connect", "status": "request", "from": from_name}))
                else:
                    msg = json.dumps({"action": "connect", "status": "no-user"})
                mysend(client, msg)

            elif msg["action"] == "exchange":
                # message exchange: send message to all peers in the group
                from_name = self.logged_sock2name[client]
                to_others_msg = json.dumps({
                    "action": "exchange",
                    "from": from_name,
                    "message": msg["message"]
                })
                self.indices[from_name] = msg["message"]
                the_guys = self.group.list_me(from_name)[1:]
                for g in the_guys:
                    to_sock = self.logged_name2sock[g]
                    mysend(to_sock, to_others_msg)

            elif msg["action"] == "disconnect":
                from_name = self.logged_sock2name[client]
                the_guys = self.group.list_me(from_name)
                self.group.disconnect(from_name)
                the_guys.remove(from_name)
                if len(the_guys) == 1:  # only one left
                    g = the_guys.pop()
                    to_sock = self.logged_name2sock[g]
                    mysend(to_sock, json.dumps({
                        "action": "disconnect",
                        "msg": "everyone left, you are alone"
                    }))

            elif msg["action"] == "list":
                # listing available peers
                msg_list = self.group.list_all
                mysend(client, json.dumps({"action": "list", "results": msg_list}))

            elif msg["action"] == "poem":
                # retrieve a sonnet
                poem = self.sonnet.get_poem(msg["target"])
                print('here:\n', poem)
                mysend(client, json.dumps({"action": "poem", "results": poem}))

            elif msg["action"] == "time":
                ctime = time.strftime('%d.%m.%y,%H:%M', time.localtime())
                mysend(client, json.dumps({"action": "time", "results": ctime}))

            elif msg["action"] == "search":
                # search chat history for keyword (simple implementation)
                target = msg["target"]
                search_rslt = ''
                for num, values in self.indices.items():
                    if target in values == True:
                        search_rslt += self.indices.values
                print('server side search: ' + search_rslt)
                mysend(client, json.dumps({"action": "search", "results": search_rslt}))

        # for register new users
            elif msg["action"] == "register":
                uname = data["name"]
                pwd = data["password"]
                if uname in self.users:
                    mysend(client, json.dumps({"action": "register_response", "status": "exists"}))
                else:
                    self.users[uname] = hashlib.sha256(pwd.encode()).hexdigest()
                    with open('users.json', 'w') as f:
                        json.dump(self.users, f)
                    mysend(client, json.dumps({"action": "register_response", "status": "success"}))

        # for logging registered users
            elif msg["action"] == "login":
                uname, pwd = data["name"], data["password"]
                if uname not in self.users:
                    mysend(client, json.dumps({"action": "login_response", "status": "no_user"}))
                else:
                    if self.users[uname] == hashlib.sha256(pwd.encode()).hexdigest():
                        self.clients[uname] = client
                        username = uname
                        mysend(client, json.dumps({"action": "login_response", "status": "success"}))
                    else:
                        mysend(client, json.dumps({"action": "login_response", "status": "wrong_pass"}))

        # so-as to handle on-server hand-written digit recognition
            elif msg["action"] == "predict":
                model_label = data["model"]  # "v1","v2","v3"
                b64 = data["image"].split(",", 1)[1]
                img = Image.open(BytesIO(base64.b64decode(b64))).convert('L')
                img = img.resize((28, 28), Image.LANCZOS)
                arr = (255 - np.array(img).astype('float32')) / 255.0
                arr = arr.reshape((1, 28, 28, 1))
                # select model
                model = getattr(self, f"cnn_model_{model_label}")
                preds = model.predict(arr)[0]
                digit = int(np.argmax(preds))
                username = data["username"]
                text = f"{username} drew {digit} with {model_label}"
                # send back to requester and peer
                msg = json.dumps({"action": "exchange", "from": username, "message": text})
                mysend(client, msg)
                if username in self.peers:
                    mysend(self.clients[self.peers[username]], msg)

        else:
            # client died unexpectedly
            self.logout(client)

    # main loop, loops forever
    def run(self):
        print('starting server...')
        while True:
            read, _, _ = select.select(self.all_sockets, [], [])
            print('checking logged clients..')
            for logc in list(self.logged_name2sock.values()):
                if logc in read:
                    try:
                        self.handle_msg(logc)
                    except Exception as e:
                        print(f"Error handling client, logging out: {e}")
                        # CHANGED: on error, log out client
                        self.logout(logc)
            print('checking new clients..')
            for newc in self.new_clients[:]:
                if newc in read:
                    try:
                        self.login(newc)
                    except Exception as e:
                        print(f"Error during login: {e}")
                        # CHANGED: on login error, remove and close new client socket
                        if newc in self.new_clients:
                            self.new_clients.remove(newc)
                        if newc in self.all_sockets:
                            self.all_sockets.remove(newc)
                        newc.close()
            print('checking for new connections..')
            if self.server in read:
                # new client connection request
                sock, address = self.server.accept()
                self.new_client(sock)

def main():
    server = Server()
    server.run()

if __name__ == '__main__':
    main()

