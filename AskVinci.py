import tkinter.messagebox as messagebox
import re
import configparser
import logging

import socket

import openai


HOST = "127.0.0.1"
PORT = 60703

CONFIG_PATH = "config"
config = configparser.ConfigParser()
config.read_file(open(CONFIG_PATH))

MODEL = config.get("AskVinci", "MODEL")
MAX_TOKENS = int(config.get("AskVinci", "MAX_TOKENS"))
TEMPERATURE = float(config.get("AskVinci", "TEMPERATURE"))
VERSION = config.get("AskVinci", "VERSION")

openai.api_key = config.get("AskVinci", "OPENAPI_KEY")


def expandasciiescapes(text: str) -> str:
    """
    Replace all ASCII escapes in a URI with their corresponding characters.

    This function expects a properly formatted URI. Any occurence of the
    character '%' must be followed by a valid two-digit uppercase hex number.
    """
    i = 0
    while i < len(text):
        if text[i] == '%':
            str1 = text[:i:]
            str2 = "%(char)c" % {'char': int(text[i + 1:i + 3:], 16)}
            str3 = text[i + 3::]
            text = str1 + str2 + str3
        i += 1

    return text


with socket.socket() as localsock:
    logging.info("socket assigned")

    try:
        localsock.bind((HOST, PORT))
        logging.info("bound to {}:{}, listening...".format(HOST, PORT))
    except socket.error as e:
        messagebox.showerror(
            "AskVinci", "AskVinci: Could not bind to {}\n{}".format(PORT, str(e)))

    localsock.listen()

    # accept loop
    while True:
        clntconn, clntaddr = localsock.accept()
        with clntconn:
            logging.info("accepted connection from {}".format(clntaddr))
            # need to allow for requests > 4096 though!
            query = str(clntconn.recv(4096))
            if not query:
                continue

            query = query.split(" ")
            if len(query) < 2:
                continue
            query = query[1][1::]

            query = expandasciiescapes(query)
            if query == "favicon.ico":
                clntconn.send(bytes("HTTP/1.0 404 Not Found", "utf-8"))
                continue

            logging.info("received query: \"{}\"".format(query))

            response = openai.Completion.create(
                model=MODEL,
                prompt=query,
                suffix="\n\n - DaVinci",
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE
            )
            
            logging.debug("OpenAI response: " + str(response))

            textline = re.search(r"\"text[ -~]+\n", str(response))
            if not textline:
                continue
            try:
                textline = textline.group(0)  # TODO: slice this
            except IndexError as e:
                messagebox.showerror(
                    "AskVinci", "Askvinci: bad response format.\n{}".format(e))

            print(textline)  # TODO: remove

            htmlbody = ("<html>\r\n"
                        "<body>\r\n"
                        + "<h1> Query: \"{}\"</h1>\r\n".format(query) +
                        "<h2>DaVinciSez:</h2>\r\n"
                        + "<p>{}</p>\r\n".format(textline) +
                        "</body>\r\n"
                        "</html>\r\n")

            message = ("HTTP/1.0 200 OK\r\n"
                       "Content-Type: text/html"
                       + "Content-Length: {}".format(len(htmlbody))
                       + "Server: AskVinci/{}".format(VERSION) +
                       "\r\n")

            clntconn.sendall(bytes(message, "utf-8"))
            clntconn.close()
            logging.info(str(clntaddr) + " closed.")
