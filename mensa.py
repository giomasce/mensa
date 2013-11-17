# -*- coding: utf-8 -*-

import sys
import os
import datetime
import pprint
import json
import urlparse
import traceback

sys.path.append(os.path.dirname(__file__))
from data import Session, User, Phase, Statement, MOMENTS
from util import html_escape

MAX_REQUEST_BODY_SIZE = 10*1024

# Just a way to quickly terminate the request
class RequestTerminator:
    pass

class MensaHandler:
    def __init__(self, environ, start_response):
        self.environ = environ
        self.start_response = start_response
        self.session = Session()
        self.status = '200 OK'
        self.output = []
        self.response_headers = []
        self.content_type = 'text/html'
        self.ref_time = datetime.datetime.now()

    def user_check(self):
        try:
            username = self.environ['REMOTE_USER']
        except KeyError:
            self.user = None
        else:
            self.user = User.get_from_username(self.session, username)
            if not self.user.enabled:
                self.user = None
        if self.user is None:
            self.error(message="Could not detect user")

    def phase_check(self):
        self.phase = Phase.get_current(self.session, self.ref_time)

    def url_check(self):
        self.path_info = self.environ['PATH_INFO']
        self.script_name = self.environ['SCRIPT_NAME']

    def post_check(self):
        if self.environ['REQUEST_METHOD'] != 'POST':
            self.error(status='405 Method Not Allowed')
        request_body_size = int(self.environ.get('CONTENT_LENGTH', 0))
        if request_body_size > MAX_REQUEST_BODY_SIZE:
            self.error(status='413 Request Entity Too Large')
        self.post_data = urlparse.parse_qs(self.environ['wsgi.input'].read(request_body_size))

    def print_home(self):
        statement = self.user.get_last_statement(self.phase)
        if statement is None or statement.value is None:
            statement_value = ''
        else:
            statement_value = statement.value
        self.output.append(u'<h1>A che ora andiamo a mensa?</h1>\n')
        self.output.append(u'Ciao utente <b>@%s</b>!<br>\n' % (self.user.get_pretty_name()))
        self.output.append(u'Queste sono le dichiarazioni per il %s a %s.<br>\n' % (self.phase.date, MOMENTS[self.phase.moment][0]))
        self.output.append(u'<br>\n')
        for statement in self.phase.get_statements():
            self.output.append(u'<b>@%s</b> (%s): %s<br>\n' % (html_escape(statement.user.get_pretty_name()), html_escape(str(statement.time.time())), html_escape(statement.value)))
        self.output.append(u'<br>\n')
        self.output.append(u'Fai la tua dichiarazione!<br>\n')
        self.output.append(u'<form method="post" action="%s/state">\n' % (self.script_name))
        self.output.append(u'<input type="text" name="statement" value="%s" size="100">\n' % (html_escape(statement_value)))
        self.output.append(u'<input type="submit" name="submit" value="Sottometti!">\n')
        self.output.append(u'</form>\n')
        self.output.append(u'<i>Buone patate!</i><br>\n')
        self.output.append(u'<a href="%s/json">JSON</a><br>\n' % (self.script_name))

    def print_debug(self):
        self.content_type = 'text/plain'
        pp = pprint.PrettyPrinter(indent=4)
        if 'path_info' in self.__dict__:
            self.output.append('Path info: %s\n' % (self.path_info))
        self.output.append(pp.pformat(self.environ))

    def receive_statement(self):
        self.post_check()
        try:
            value = self.post_data.get('statement', [])[0].decode('utf-8')
        except IndexError:
            value = None
        self.user.add_statement(self.phase, self.ref_time, value)
        self.redirect(self.script_name)

    def print_json_statements(self):
        self.content_type = 'application/json'
        ret = {'statements': []}
        for statement in self.phase.get_statements():
            ret['statements'].append({'username': statement.user.get_pretty_name(),
                                      'value': statement.value})
        self.output.append(json.dumps(ret))

    def error(self, status=None, message=None):
        self.status = status
        if self.status is None:
            self.status = '500 Internal Server Error'
        self.output = ['<h1>Error: %s</h1>' % (self.status)]
        if message is not None:
            self.output.append('%s' % (message))
        raise RequestTerminator()

    def redirect(self, where):
        self.status = '302 Found'
        self.response_headers += (('Location', where),)
        self.output = []
        raise RequestTerminator()

    def finish(self):
        self.session.commit()
        self.output = "".join(self.output).encode('utf-8')
        self.response_headers += [('Content-Type', '%s; charset=utf-8' % (self.content_type)),
                                  ('Content-Length', str(sum(map(lambda x: len(x), self.output))))]
        self.start_response(self.status, self.response_headers)

    EMERGENCY_DEBUG = False
    PRINT_ERROR = True

    def __call__(self):
        try:
            self.url_check()

            if MensaHandler.EMERGENCY_DEBUG:
                self.print_debug()
                self.finish()
                return [self.output]

            self.user_check()
            self.phase_check()

            if self.path_info == '':
                self.print_home()
            elif self.path_info == '/json':
                self.print_json_statements()
            elif self.path_info == '/debug':
                self.print_debug()
            elif self.path_info == '/state':
                self.receive_statement()
            else:
                self.redirect(self.script_name)

        except RequestTerminator:
            pass

        except:
            try:
                message = None
                if MensaHandler.PRINT_ERROR:
                    message = u'<pre>%s</pre>' % (html_escape(traceback.format_exc()))
                self.error(message=message)
            except RequestTerminator:
                pass

        self.finish()
        return [self.output]

class MensaApp:

    def __init__(self):
        pass

    def __call__(self, environ, start_response):
        handler = MensaHandler(environ, start_response)
        return handler()

application = MensaApp()
