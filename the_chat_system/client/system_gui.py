import tkinter as tk
from tkinter import simpledialog, messagebox
import subprocess
import sys
import webbrowser
import threading
from chat_utils import *
from indexer_student import *
from client_state_machine import ClientSM
from chat_server import NeuralNetworks
import socket
import json
import io, base64, numpy as np
import os
from PIL import Image, ImageTk, ImageGrab

# READ THIS: before running this code, run chat_server.py first to make sure it's listening thus we can log in
# READ THIS: there are three amazing neural networks models, to let them work in full glory, please recognize on the
    # canvas inside the gui, as the canvas in the online demo is not as good as this one
# READ THIS: if you'd also like to try the online demo, please run app.py to load the webpage before hitting the button for online demo
# REMARK: the order of running files: first run chat_server.py (and app.py for optional webpage demo (unnecessary)), then run system_gui.py

# Credits: many credits due to nyush icds team and professors, many credits due to the three collaborators, namely,
    # justin, jenson and walter, some credits due to chatgpt.com for refining the codes for the neural network codes, but
    # in the other parts it was not helping too much and always causing troubles
# Thanks: Great thanks to nyush icds team and professors, and Michael Neilson's 2019 book, as cited in the presentation video
# Final remarks: this is a very interesting experience and chance, i've learnt a lot about many things.
    # thank you all: professors, teammates, online educators, writers, chatgpt.com, and me myself. I love you guys so much


# Constants (adjust paths as needed)
SERVER = ('127.0.0.1', 12345)  # the chat server address
APP_PY_PATH = '/Users/justinbian/PycharmProjects/hand_written_digit_recognition_CNN/app.py'


class YouAreAWizardHarry(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("You're a wizard Harry")
        self.geometry("1000x600")
        self.configure(bg="#f5f7fa")
        self.chat_display = None
        self.state_label = None

        tk.Label(self, text="Username:").place(x=20, y=20)
        self.username_entry = tk.Entry(self)
        self.username_entry.place(x=100, y=20)
        tk.Label(self, text="Password:").place(x=20, y=50)
        self.password_entry = tk.Entry(self, show='*')
        self.password_entry.place(x=100, y=50)


        # now let's add self.log_in_buttons()
        self.login_btn = tk.Button(self, text="Login", command=self.handle_login)
        self.login_btn.place(x=300, y=50)
        self.register_btn = tk.Button(self, text="Register", command=self.handle_register)
        self.register_btn.place(x=400, y=50)

        # then let's set self.s
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.s.connect(SERVER)  # SERVER = (host, port) tuple

            print("Connected to server at", SERVER)

        except Exception as e:
            messagebox.showerror("Connection Error", f"Cannot connect: {e}")
            self.destroy()
            return

        # now create an instance of ClientSM
        self.client_sm = ClientSM(self.s)

        # here we create an instance of NeuralNetworks, so-as to load and call the neural network locally
        self.neural_networks = NeuralNetworks()


    def log_in_buttons(self):
        tk.Button(self, text="Login", command=self.handle_login).place(x=250, y=20)
        tk.Button(self, text="Register", command=self.handle_register).place(x=250, y=50)

    def handle_register(self):
        uname = self.username_entry.get().strip()
        pwd = self.password_entry.get().strip()
        req = json.dumps({"action": "register", "name": uname, "password": pwd})

        print("CLIENT →", req)

        mysend(self.s, req)
        raw = myrecv(self.s)
        if not raw:
            messagebox.showerror("Register", "No response from server")
            return
        try:
            resp = json.loads(raw)
        except Exception as e:
            messagebox.showerror("Register", "Bad response: " + str(e))
            return
        if resp.get("status") == "exists":
            messagebox.showerror("Register", "Username exists")
        else:
            messagebox.showinfo("Register", "Registration successful")

    def handle_login(self):
        uname = self.username_entry.get().strip()
        pwd = self.password_entry.get().strip()
        req = json.dumps({"action": "login", "name": uname, "password": pwd})
        mysend(self.s, req)

        print("CLIENT →", req)

        raw = myrecv(self.s)
        if not raw:
            messagebox.showerror("Login", "No response from server")
            return
        try:
            resp = json.loads(raw)
        except Exception as e:
            messagebox.showerror("Login", "Bad response: " + str(e))
            return
        st = resp.get("status")
        if st == "no_user":
            messagebox.showinfo("Login", "User not found; please register")
            return
        if st == "wrong_pass":
            messagebox.showerror("Login", "Wrong password")
            return

        messagebox.showinfo("Login", "Login successful")
        self.login_btn.place_forget()
        self.register_btn.place_forget()
        self.client_sm.set_state(S_LOGGEDIN)

        # now we can set the username, as we've got it now
        self.client_sm.set_myname(self.username_entry.get().strip())

        # and now after successfully logged in, let's set the other parts of the gui to let it cook
        self.sidebar_width = 160
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.icons = {}
        self.load_icons()
        self.create_top_bar()
        self.create_side_bar()
        self.create_main_area()

    def update_chat_display(self, text):
        if self.chat_display:
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.insert(tk.END, text + "\n")
            self.chat_display.config(state=tk.DISABLED)
            self.chat_display.see(tk.END)

    def load_icons(self):
        icon_names = ["chat", "tools", "logo"]
        for name in icon_names:
            path = os.path.join(os.path.dirname(__file__), 'icons', f"{name}.png")
            try:
                img = Image.open(path)
                size = (40, 40) if name == "logo" else (20, 20)
                img = img.resize(size, Image.Resampling.LANCZOS)
                self.icons[name] = ImageTk.PhotoImage(img)
            except Exception as e:
                print(f"Failed to load icon {name}: {e}")
                self.icons[name] = None

    def create_top_bar(self):
        top_bar = tk.Frame(self, height=60, bg="#3c8dbc")
        top_bar.grid(row=0, column=0, columnspan=2, sticky="new")
        if self.icons.get("logo"):
            tk.Label(top_bar, image=self.icons["logo"], bg="#3c8dbc").pack(side="left", padx=10)
        tk.Label(top_bar, text="Swish and Flick: The Hogwarts Server System", font=("Helvetica", 21), fg="white",
                 bg="#3c8dbc").pack(side="left")

    def create_side_bar(self):
        side_bar = tk.Frame(self, width=self.sidebar_width, bg="#ecf0f1")
        side_bar.grid(row=1, column=0, sticky="ns")
        buttons = [
            ("Chat", self.icons.get("chat"), self.show_chat),
            ("Tools", self.icons.get("tools"), self.show_tools),
            ("Hand Written Digit Recognizer Webpage Demo", None, self.launch_server)
        ]
        for label, icon, cmd in buttons:
            btn = tk.Button(
                side_bar, text=f"  {label}", image=icon, compound="left",
                command=cmd, bg="#ecf0f1", relief="flat", anchor="w"
            )
            btn.pack(fill="x", pady=5, padx=10)

    def create_main_area(self):
        self.main_area = tk.Frame(self, bg="#f5f7fa")
        self.main_area.grid(row=1, column=1, sticky="nsew")
        self.main_area.grid_rowconfigure(0, weight=1)
        self.main_area.grid_columnconfigure(0, weight=1)
        self.content_frame = tk.Frame(self.main_area, bg="white")
        self.content_frame.grid(row=0, column=0, sticky="nsew")

    def clear_content(self):
        for w in self.content_frame.winfo_children():
            w.destroy()

    # we also need a method to load our online demo
    def launch_server(self):
        def run():
            os.chdir(os.path.dirname(APP_PY_PATH))
            subprocess.call([sys.executable, APP_PY_PATH])

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        time.sleep(1)
        webbrowser.open('http://127.0.0.1:5000/')

    def show_chat(self):
        self.clear_content()
        tk.Label(self.content_frame, text="📨 Chat zone", font=("Arial", 16)).pack(pady=10)

        # here we fill in the blank space for chat_display
        self.chat_display = tk.Text(self.content_frame, state='disabled', wrap=tk.WORD, height=5)
        self.chat_display.pack(fill=tk.BOTH, expand=True)

        # and we also need something to hold on to for the state of the user
        self.state_label = tk.Label(self.content_frame, text="State: Unknown", font=("Arial", 12), anchor="w")
        self.state_label.pack(pady=(5, 0))

        # here, for further utility, we create a scrollable chat window
        self.chat_display = tk.Text(self.content_frame, state='disabled', wrap=tk.WORD, height=15)
        self.chat_display.pack(fill=tk.BOTH, expand=True)

        # here we create the input frame for entering text, which will be used as a parameter in the message entry part
        input_frame = tk.Frame(self.content_frame)
        input_frame.pack(fill=tk.X, pady=(5, 10))

        # here we also add a place for entering chat messages
        self.msg_entry = tk.Entry(input_frame)
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.msg_entry.bind("<Return>", self.handle_chat)

        # Add chat buttons
        # for label in ["Chat", "Search", "Who", "Connect", "Disconnect"]:
        tk.Button(self.content_frame, text="Chat", command=self.handle_chat, width=25, height=2, bg="#f0f0f0").pack(
            pady=5)
        tk.Button(self.content_frame, text="Search", command=self.handle_search, width=25, height=2, bg="#f0f0f0").pack(
            pady=5)
        tk.Button(self.content_frame, text="Check who's online (but not answering your texts 🤣)",
                  command=self.handle_who, width=35, height=2, bg="#f0f0f0").pack(pady=5)
        tk.Button(self.content_frame, text="Connect", command=self.handle_connect, width=25, height=2,
                  bg="#f0f0f0").pack(pady=5)
        tk.Button(self.content_frame, text="Disconnect", command=self.handle_disconnect, width=25, height=2,
                  bg="#f0f0f0").pack(pady=5)

    def update_state_display(self):
        names = {S_OFFLINE: 'Offline', S_LOGGEDIN: 'Logged In', S_CHATTING: 'Chatting'}
        state_name = names.get(self.client_sm.get_state(), 'Logged In')
        self.state_label.config(text=f"State: {state_name}")

    def handle_connect(self):
        peer = simpledialog.askstring("Connect", "Peer name:", parent=self)
        if not peer:
            return

        connected = self.client_sm.connect_to(peer)
        self.update_chat_display(self.client_sm.out_msg)

        if connected:
            self.client_sm.set_state(S_CHATTING)
        self.update_state_display()

    def handle_search(self):
        term = simpledialog.askstring("Search", "Search term:", parent=self)
        if not term:
            return

        self.client_sm.proc(f"?{term}", "")
        self.update_chat_display(self.client_sm.out_msg)
        self.update_state_display()

    def handle_who(self):
        self.client_sm.proc('who', '')
        self.update_chat_display(self.client_sm.out_msg)
        self.update_state_display()

    def handle_disconnect(self):
        self.client_sm.disconnect()
        self.update_chat_display(self.client_sm.out_msg)
        self.client_sm.set_state(S_LOGGEDIN)
        self.update_state_display()

    def handle_chat(self, event=None):
        msg = simpledialog.askstring("Chat", "Enter your message:", parent=self)
        if not msg:
            return

        self.client_sm.proc(msg, '')
        self.update_chat_display(self.client_sm.out_msg)
        self.update_state_display()

    def show_tools(self):
        self.clear_content()
        tk.Label(self.content_frame, text="🛠 Tools", font=("Arial", 16)).pack(pady=10)

        # Add tools buttons
        tk.Button(self.content_frame, text="Time", command=self.show_time, width=25, height=2, bg="#f0f0f0").pack(
            pady=5)
        tk.Button(self.content_frame, text="Get Poem", command=self.handle_poem, width=25, height=2, bg="#f0f0f0").pack(
            pady=5)

        # Add CNN canvas section
        tk.Label(self.content_frame, text='✍ CNN Canvas: "πlease" draw your digit', font=("Arial", 14)).pack(pady=10)
        self.canvas = tk.Canvas(self.content_frame, bg="white", width=200, height=200, relief="ridge", bd=2)
        self.canvas.pack(pady=5)
        self.canvas.bind("<B1-Motion>", self.paint)
        self.prev_x = None
        self.prev_y = None

        # Add recognition buttons
        tk.Button(self.content_frame, text='recognize with v1', command=self.predict_drawing_v1, width=20).pack(pady=5)
        tk.Button(self.content_frame, text='recognize with v2', command=self.predict_drawing_v2, width=20).pack(pady=5)
        tk.Button(self.content_frame, text='recognize with v3', command=self.predict_drawing_v3, width=20).pack(pady=5)
        tk.Button(self.content_frame, text="clear canvas", command=self.clear_canvas, width=20).pack()

        tk.Button(self, text="Server side v1", command=lambda: self.predict_server("v1")).place(x=80, y=480)
        tk.Button(self, text="Server side v2", command=lambda: self.predict_server("v2")).place(x=80, y=510)
        tk.Button(self, text="Server side v3", command=lambda: self.predict_server("v3")).place(x=80, y=540)

        # Start receive thread
        threading.Thread(target=self.receive_messages, daemon=True).start()

    def show_time(self):
        current_time = time.strftime("%H:%M:%S", time.localtime())
        messagebox.showinfo("Current Time", f"Current time is: {current_time}")

    def handle_poem(self):
        num = simpledialog.askinteger("Poem", "Enter sonnet number:")
        if num:
            self.get_poem(num)
            # self.send_command(num)

    def get_poem(self, p):

        obj = PIndex("AllSonnets.txt")
        print(obj)
        poem = obj.get_poem(p)
        if poem:
            messagebox.showinfo("Poem", poem)
        else:
            messagebox.showwarning("Poem", "Failed to retrieve poem.")
        return poem

    # New methods from
    def paint(self, event):
        if self.prev_x and self.prev_y:
            self.canvas.create_line(self.prev_x, self.prev_y, event.x, event.y, width=5)
        self.prev_x = event.x
        self.prev_y = event.y

    def clear_canvas(self):
        self.canvas.delete("all")
        self.prev_x = None
        self.prev_y = None

    def predict_drawing_v1(self):
        # 1) Grab canvas area from the screen
        x = self.canvas.winfo_rootx()
        y = self.canvas.winfo_rooty()
        w = x + self.canvas.winfo_width()
        h = y + self.canvas.winfo_height()
        img = ImageGrab.grab((x, y, w, h)).convert('L')  # grayscale

        # 2) Resize to 28×28 and invert colors (white on black → black on white)
        img = img.resize((28, 28), Image.LANCZOS)
        arr = np.array(img).astype('float32')
        # when loading v3, only run this line
        arr = 255.0 - arr
        # when loading v1 or v2, also run this line
        arr = arr / 255.0
        arr = arr.reshape((1, 28, 28, 1))

        # 3) Predict with your CNN
        prediction = self.neural_networks.cnn_model_v1.predict(arr)[0]  # shape (10,)
        digit = int(np.argmax(prediction))
        confidence = prediction[digit]

        # 4) Show the result
        messagebox.showinfo(
            "Prediction",
            f"I think you drew a {digit}  \nConfidence: {confidence * 100:.1f}%"
        )

    def predict_drawing_v2(self):
        # 1) Grab canvas area from the screen
        x = self.canvas.winfo_rootx()
        y = self.canvas.winfo_rooty()
        w = x + self.canvas.winfo_width()
        h = y + self.canvas.winfo_height()
        img = ImageGrab.grab((x, y, w, h)).convert('L')  # grayscale

        # 2) Resize to 28×28 and invert colors (white on black → black on white)
        img = img.resize((28, 28), Image.LANCZOS)
        arr = np.array(img).astype('float32')
        # when loading v3, only run this line
        arr = 255.0 - arr
        # when loading v1 or v2, also run this line
        arr = arr / 255.0
        arr = arr.reshape((1, 28, 28, 1))

        # 3) Predict with your CNN
        prediction = self.neural_networks.cnn_model_v2.predict(arr)[0]  # shape (10,)
        digit = int(np.argmax(prediction))
        confidence = prediction[digit]

        # 4) Show the result
        messagebox.showinfo(
            "Prediction",
            f"I think you drew a {digit}  \nConfidence: {confidence * 100:.1f}%"
        )

    def predict_drawing_v3(self):
        # 1) Grab canvas area from the screen
        x = self.canvas.winfo_rootx()
        y = self.canvas.winfo_rooty()
        w = x + self.canvas.winfo_width()
        h = y + self.canvas.winfo_height()
        img = ImageGrab.grab((x, y, w, h)).convert('L')  # grayscale

        # 2) Resize to 28×28 and invert colors (white on black → black on white)
        img = img.resize((28, 28), Image.LANCZOS)
        arr = np.array(img).astype('float32')
        # when loading v3, only run this line
        arr = 255.0 - arr
        # when loading v1 or v2, also run this line
        # arr = arr / 255.0
        arr = arr.reshape((1, 28, 28, 1))

        # 3) Predict with your CNN
        prediction = self.neural_networks.cnn_model_v3.predict(arr)[0]  # shape (10,)
        digit = int(np.argmax(prediction))
        confidence = prediction[digit]

        # 4) Show the result
        messagebox.showinfo(
            "Prediction",
            f"I think you drew a {digit}  \nConfidence: {confidence * 100:.1f}%"
        )

    def predict_server(self, model_id):
        # 1) capture canvas as PostScript, convert to PNG
        ps = self.canvas.postscript(colormode='mono')
        img = Image.open(io.BytesIO(ps.encode('utf-8'))).convert('L')
        img = img.resize((28, 28), Image.LANCZOS)
        img = Image.eval(img, lambda x: 255 - x)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        b64 = base64.b64encode(buf.getvalue()).decode()
        data = f"data:image/png;base64,{b64}"
        req = json.dumps({"action": "predict", "model": model_id, "image": data})
        mysend(self.client, req)


if __name__ == "__main__":
    app = YouAreAWizardHarry()
    app.mainloop()



