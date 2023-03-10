# Copyright (C) 2023 Noam E Bechhofer
# Text art: https://patorjk.com/software/taag/

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


#      _        _   __     ___            _
#     / \   ___| | _\ \   / (_)_ __   ___(_)
#    / _ \ / __| |/ /\ \ / /| | '_ \ / __| |
#   / ___ \\__ \   <  \ V / | | | | | (__| |
#  /_/   \_\___/_|\_\  \_/  |_|_| |_|\___|_|
import openai
import socket
import logging
import configparser
import codecs
import re
import tkinter.messagebox as messagebox
VERSION = "0.0.0"


HOST = "127.0.0.1"
PORT = 60703

CONFIG_PATH = "config"
config = configparser.ConfigParser()
config.read_file(open(CONFIG_PATH))

MODEL = config.get("AskVinci", "MODEL")
MAX_TOKENS = int(config.get("AskVinci", "MAX_TOKENS"))
TEMPERATURE = float(config.get("AskVinci", "TEMPERATURE"))

openai.api_key = config.get("AskVinci", "OPENAPI_KEY")

ESCAPE_SEQUENCE_RE = re.compile(r'''
    ( \\U........      # 8-digit hex escapes
    | \\u....          # 4-digit hex escapes
    | \\x..            # 2-digit hex escapes
    | \\[0-7]{1,3}     # Octal escapes
    | \\N\{[^}]+\}     # Unicode characters by name
    | \\[\\'"abfnrtv]  # Single-character escapes
    )''', re.UNICODE | re.VERBOSE)


def decode_escapes(text: str) -> str:
    """
    Replace all escapes in a string with their corresponding characters.
    """
    def decode_match(match):
        return codecs.decode(match.group(0), 'unicode-escape')

    return ESCAPE_SEQUENCE_RE.sub(decode_match, text)


def decode_formatters(text: str) -> str:
    """
    Replace all format specifications in a URI with their corresponding characters.

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

            query = str(clntconn.recv(4096))
            # while len(nextblock := clntconn.recv(4096)) > 0:
            #     query += str(nextblock)

            if not query:
                continue

            query = query.split(" ")
            if len(query) < 2:
                continue
            query = query[1][1::]

            query = decode_formatters(query)
            if query == 'favicon.ico':
                clntconn.sendall(bytes("HTTP/1.0 200 OK\r\n"
                                       "Content-Type: image/x-icon\r\n"
                                       + "Server: AskVinci/{}\r\n".format(VERSION) +
                                       "\r\n",
                                       "utf-8"))
                clntconn.sendfile(open("favicon.ico", "rb"))
                clntconn.close()
                continue

            logging.info("received query: \"{}\"".format(query))

            response = openai.Completion.create(
                model=MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant."
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                suffix="\n\n - DaVinci",
                temperature=TEMPERATURE
            )

            logging.debug("OpenAI response: " + str(response))

            response = response['choices'][0]['message']['content']
            if not response:
                continue
            completion = ""
            try:
                completion = response.group(0)  # group 0 is the entire match
                # grab the completion
                completion = decode_escapes(completion[9:len(completion) - 2:])
            except IndexError as e:
                messagebox.showerror(
                    "AskVinci", "Askvinci: bad response format.\n{}".format(e))

            htmlbody = ("<html>\r\n"
                        "<body>\r\n"
                        "<h1>DaVinciSez:</h1>\r\n"
                        + "<i>{}</i>{}\r\n".format(query, completion.replace("\n", "<br>")) +
                        "</body>\r\n"
                        "</html>\r\n")

            message = ("HTTP/1.0 200 OK\r\n"
                       "Content-Type: text/html\r\n"
                       + "Content-Length: {}\r\n".format(len(htmlbody))
                       + "Server: AskVinci/{}\r\n".format(VERSION) +
                       "\r\n"
                       + htmlbody)

            clntconn.sendall(bytes(message, "utf-8"))
            clntconn.close()
            logging.info(str(clntaddr) + " closed.")
