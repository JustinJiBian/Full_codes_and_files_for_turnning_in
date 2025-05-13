from cryptography.fernet import Fernet

# Shared symmetric key (32-byte URL-safe base64, e.g. Fernet.generate_key())
# for personalized keys:
# KEY = b'your_base64_key_here'
KEY = Fernet.generate_key()
the_oracle = Fernet(KEY)

def encrypt_message(msg: str) -> str:
    return the_oracle.encrypt(msg.encode()).decode()

def decrypt_message(token: str) -> str:
    return the_oracle.decrypt(token.encode()).decode()

"""
Created on Sun Apr  5 00:00:32 2015

@author: zhengzhang
"""
from chat_utils import *
import json


class ClientSM:
    def __init__(self, s):
        self.state = S_OFFLINE
        self.peer = ''
        self.me = ''
        self.out_msg = ''
        self.s = s

    def set_state(self, state):
        self.state = state

    def get_state(self):
        return self.state

    def set_myname(self, name):
        self.me = name

    def get_myname(self):
        return self.me

    def connect_to(self, peer, msg=None):
        msg = json.dumps({"action": "connect", "target": peer})
        mysend(self.s, msg)
        response = json.loads(myrecv(self.s))
        if response["status"] == "success":
            self.peer = peer
            self.out_msg += 'You are connected with ' + self.peer + '\n'
            return True
        elif response["status"] == "busy":
            self.out_msg += 'Well the user is "busy", please try again later\n'
        elif response["status"] == "self":
            self.out_msg += "Well you're trying to talk to yourself\n"
        else:
            self.out_msg += 'Well the user is not logged in yet\n'
        return False

    def disconnect(self):
        msg = json.dumps({"action": "disconnect"})
        mysend(self.s, msg)
        self.out_msg += 'You are disconnected from ' + self.peer + '\n'
        self.peer = ''

    def proc(self, my_msg, peer_msg):
        handled = False  # Track whether something was successfully handled
        self.out_msg = ''
        # ==============================================================================
        # Once logged in, do a few things: get peer listing, connect, search
        # And, of course, if you are so bored, just go
        # This is event handling instate "S_LOGGEDIN"
        # ==============================================================================
        if self.state == S_LOGGEDIN:
            # todo: can't deal with multiple lines yet # well for now we're still not handling this issue
            if len(my_msg) > 0:

                if my_msg == 'q':
                    self.out_msg += 'See you next time!\n'
                    self.state = S_OFFLINE

                elif my_msg == 'time':
                    mysend(self.s, json.dumps({"action": "time"}))
                    time_in = json.loads(myrecv(self.s))["results"]
                    self.out_msg += "Time is: " + time_in

                elif my_msg == 'who':
                    mysend(self.s, json.dumps({"action": "list"}))
                    logged_in = json.loads(myrecv(self.s))["results"]
                    self.out_msg += 'Here are all the users in the system:\n'
                    self.out_msg += logged_in

                elif my_msg[0] == 'c':
                    peer = my_msg[1:]
                    peer = peer.strip()
                    if self.connect_to(peer) == True:
                        self.state = S_CHATTING
                        self.out_msg += 'Connect to ' + peer + '. Chat away!\n\n'
                        self.out_msg += '-----------------------------------\n'
                    else:
                        self.out_msg += 'Connection unsuccessful\n'

                elif my_msg[0] == '?':
                    term = my_msg[1:].strip()
                    mysend(self.s, json.dumps({"action": "search", "target": term}))
                    search_rslt = json.loads(myrecv(self.s))["results"].strip()
                    if (len(search_rslt)) > 0:
                        self.out_msg += search_rslt + '\n\n'
                    else:
                        self.out_msg += '\'' + term + '\'' + ' not found\n\n'

                elif my_msg[0] == 'p' and my_msg[1:].isdigit():
                    poem_idx = my_msg[1:].strip()
                    mysend(self.s, json.dumps({"action": "poem", "target": poem_idx}))
                    poem = json.loads(myrecv(self.s))["results"]
                    if (len(poem) > 0):
                        self.out_msg += poem + '\n\n'
                    else:
                        self.out_msg += 'Sonnet ' + poem_idx + ' not found\n\n'

                else:
                    self.out_msg += menu

            if len(peer_msg) > 0:
                try:
                    peer_msg = json.loads(peer_msg)
                except Exception as err:
                    self.out_msg += " json.loads failed " + str(err)
                    return self.out_msg

                if peer_msg["action"] == "connect":
                    self.peer = peer_msg["from"]
                    self.state = S_CHATTING
                    self.out_msg += "You are connected with " + self.peer + "\n"
                    self.out_msg += "-----------------------------------\n"
                    handled = True  # <- update this instead of returning immediately
                    return handled






        # ==============================================================================
        # Start chatting, 'bye' for quit
        # This is event handling instate "S_CHATTING"
        # ==============================================================================
        elif self.state == S_CHATTING:
            if len(my_msg) > 0:  # my stuff going out

                # mysend(self.s, json.dumps({"action": "exchange", "from": "[" + self.me + "]", "message": my_msg}))

                #let's do the encryption before sending out the message
                encrypted_msg = encrypt_message(my_msg)
                mysend(self.s, json.dumps({"action": "exchange", "from": "[" + self.me + "]", "message": encrypted_msg}))

                self.out_msg += my_msg
                if my_msg == 'bye':
                    self.disconnect()
                    self.state = S_LOGGEDIN
                    self.peer = ''
            if len(peer_msg) > 0:  # peer's stuff, coming in

                # ----------your code here------#
                peer_msg = json.loads(peer_msg)
                print(peer_msg)
                if peer_msg["action"] == "exchange":
                    # self.out_msg += peer_msg["from"] + ": " + peer_msg["message"] + "\n"

                    # and here also, we've received the encrypted message, so let's decrypt it
                    original_text = decrypt_message(peer_msg["message"])
                    self.out_msg += peer_msg["from"] + ": " + original_text + "\n"

                elif peer_msg["action"] == "disconnect":
                    self.out_msg += "Your peer has disconnected.\n"
                    self.state = S_LOGGEDIN
                    self.peer = ''

                elif peer_msg["action"] == "connect":
                    self.out_msg += "You are already connected with " + self.peer + "\n"
                    self.state = S_LOGGEDIN
                    self.peer = ''
                    return True

                # ----------end of your code----#

            # Display the menu again
            if self.state == S_LOGGEDIN:
                self.out_msg += menu
        # ==============================================================================
        # invalid state
        # ==============================================================================
        else:
            self.out_msg += 'this is the strongest else case for the text; so you have missed all the conditions, and probably for good reasons\n'
            print_state(self.state)

            return handled if handled else self.out_msg
