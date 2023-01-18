import tkinter.messagebox as messagebox
import socket

HOST = "127.0.0.1"
PORT = 60504  # random pick idk

def expandasciiescapes(text: str) -> str:
    i = 0
    while i < len(text):
        if text[i] == '%':
            str1 = text[:i:]
            str2 = "%(char)c" % {'char': int(text[i + 1:i + 3:], 16)}
            str3 = text[i + 3::]  # what if % is later than 3rd to last?
            text = str1 + str2 + str3
        i += 1
    
    return text

with socket.socket() as localsock:
    try:
        localsock.bind((HOST, PORT))
        print("bound to {}:{}, listening...".format(HOST, PORT))
    except socket.error as e:
        messagebox.showerror(
            "AskVinci", "AskVinci: Could not bind to {}\n{}".format(PORT, str(e)))

    localsock.listen()

    clntconn, clntaddr = localsock.accept()
    with clntconn:
        print("accepted connection from {}".format(clntaddr))
        query = str(clntconn.recv(4096)).split(" ")[1][1::]  # grab the URI
        query = expandasciiescapes(query)
    print("received request: \"{}\"".format(query))



