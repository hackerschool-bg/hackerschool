__author__ = 'Ivan Dortulov'

import re
import queue
import os
import stat
from Log import *


class HttpRequest(object):

    def __init__(self, request_string):
        request_string = request_string.lower()
        idx = request_string.find("\r\n")
        self.request_line = request_string[:idx].split()
        request_string = request_string[idx + 2:]

        self.headers = dict(re.findall(r"(?P<name>.*?): (?P<value>.*?)\r\n", request_string))

        self.request_method = self.request_line[0]
        self.request_uri = self.request_line[1]
        self.request_version = self.request_line[2]

        self.remaining = 0
        self.processing = False
        self.is_script = False
        self.abs_path = ""

class RequestHandler(object):

    responses = {200: "OK",
                 404: "File Not Found"}

    def __init__(self, server, address=""):
        self.server = server
        self.address = address

        self.input = b""
        self.output = b""
        self.should_close = False

        self.current_request = None
        self.request_queue = queue.Queue()
        self.request_resource = None

    def __del__(self):
        if self.request_resource is not None:
            try:
                self.request_resource.close()
            except IOError:
                Log.w("RequestHandler", "Destructor: nothing to close.")

    def process_data(self, data):
        self.input += data

    def finish_request(self):
        Log.d("RequestHandler", "process_next_request: " + self.current_request.request_line[0] +
              " request from " + str(self.address) + " was processed.")
        del self.current_request
        self.current_request = None

        if self.request_resource is not None:
            try:
                self.request_resource.close()
                self.request_resource = None
            except IOError as ex:
                Log.w("RequestHandler", "process_next_request: " + self.address +
                      "Unable to close file: " + str(ex.args[1]))

        #if self.current_request.headers["connection"] == "keep-alive":
        #    pass
        #if self.current_request.request_version == "1.1":
        #    pass

        self.should_close = True

    def process_next_request(self):
        if self.current_request is not None:
            if self.current_request.processing:
                if self.current_request.remaining <= 0:
                    if not self.current_request.is_script:
                        self.finish_request()
                    else:
                        self.process_script()
                else:
                    if self.current_request.request_method == "get":
                        self.process_get_request()
            else:
                del self.current_request
                self.current_request = None
        else:
            if not self.request_queue.empty():
                Log.d("RequestHandler", "process_next_request: Processing next request from " + self.address)
                self.current_request = self.request_queue.get(False)
                self.init_request(self.current_request)
            else:
                idx = self.input.find(b"\r\n\r\n")
                if idx >= 0:
                    request_string = self.input[:idx + 4].decode()
                    self.input = self.input[idx + 4:]

                    request = HttpRequest(request_string)
                    self.request_queue.put(request)
                    Log.d("RequestHandler", "process_data: Received " + request.request_method + " request from " +
                          self.address)

    def process_script(self):
        pass

    def process_get_request(self):
        # Check if file still exists
            try:
                if os.stat(self.current_request.abs_path)[stat.ST_SIZE] <= 0:
                    raise IOError(-1, "File deleted!")
                read_chunk = self.request_resource.read(self.server.CHUNK_SIZE)
            except IOError as ex:
                Log.w("RequestHandler", "process_get_request: " + self.address +
                      " Error reading file: " + str(ex.args[1]))
                self.current_request.remaining = 0
            else:
                Log.d("RequestHandler", "process_get_request: " + self.address +
                      " Read " + str(len(read_chunk)) + " bytes from " +
                      self.current_request.request_uri)
                self.output += read_chunk
                self.current_request.remaining -= len(read_chunk)

    def init_request(self, request):
        Log.d("RequestHandler", "init_request: " + self.address + " Initializing request")

        if request.request_method == "get":
            file_path = self.server.server_variables["document_root"] + "/public_html" + \
                        self.current_request.request_uri
            file_path = file_path.replace("\\", "/")
            self.current_request.abs_path = file_path

            Log.d("RequestHandler", "init_request: " + self.address + " requested " + self.current_request.request_uri)
            if os.path.isfile(file_path):
                (file_name, file_ext) = os.path.splitext(os.path.basename(file_path))

                if file_ext == ".py":
                    Log.d("RequestHandler", "init_request: " + self.address + " requested a script execution '" +
                          self.current_request.request_uri)
                    pass
                elif file_ext == ".php":
                    pass
                else:
                    try:
                        self.request_resource = open(file_path, "rb")
                    except IOError as ex:
                        Log.w("RequestHandler", "init_request: Could not open file '" + file_path + "': " + str(ex.args[1]))
                        self.current_request.remaining = 0
                    else:
                        (file_name, file_ext) = os.path.splitext(os.path.basename(file_path))
                        file_size = os.path.getsize(file_path)

                        Log.d("RequestHandler", "init_request: " + self.address + " File '" + file_path + "' was found(" +
                              str(file_size) + ")")

                        self.output += self.generate_response(200, "1.1", {"Content-Type": self.guess_content_type(file_ext),
                                                                           "Content-Length": str(file_size),
                                                                           "Connection": "close"}).encode()
                        self.current_request.remaining = file_size
                        self.current_request.processing = True
            elif os.path.isdir(file_path):
                Log.w("RequestHandler", "init_request: Directory listing not implemented!")
                self.current_request.remaining = 0
                self.current_request.processing = False
            else:
                self.output += self.generate_response(404, "1.1", {"Content-Type": "text/html",
                                                                   "Connection": "close"},
                                                      "<html><body><h1>404 - File not found</h1>"
                                                      "<p>The requested resource was not found on this server!</p>"
                                                      "</body></html>").encode()

                self.current_request.remaining = 0
                self.current_request.processing = False

    @staticmethod
    def generate_response(code = 200, version="1.1", headers={}, extra=""):
        if code == 200:
            response = "HTTP/" + version + str(code) + " " + RequestHandler.responses[code] + "\r\n"
            for (key, value) in headers.items():
                response += str(key) + ": " + str(value) + "\r\n"

            response += "\r\n"
            return response
        if code >= 400:
            response = "HTTP/" + version + str(code) + " " + RequestHandler.responses[code] + "\r\n"
            for (key, value) in headers.items():
                response += str(key) + ": " + str(value) + "\r\n"
            response += "Content-Length: " + str(len(extra)) + "\r\n"

            response += "\r\n"
            response += extra
            return response

    @staticmethod
    def guess_content_type(ext):
        if ext == ".txt":
            return "text/plain"
        elif ext == ".html":
            return "text/html"
        elif ext == ".css":
            return "text/css"
        elif ext == ".js":
            return "application/javascript"
        elif ext == ".png":
            return "image/png"
        else:
            return "application/octet-stream"