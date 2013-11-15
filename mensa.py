
import sys
import os
import datetime
import pprint
import json
import urlparse

sys.path.append(os.path.dirname(__file__))
from data import Session, User, Phase, Statement, MOMENTS
from util import html_escape

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

    def phase_check(self):
        self.phase = Phase.get_current(self.session, self.ref_time)

    def url_check(self):
        # TODO - Is this the right way?
        script_name = self.environ['SCRIPT_NAME']
        script_url = self.environ['SCRIPT_URL']
        assert(script_url.startswith(script_name))
        self.url_breakdown = script_url[len(script_name)+1:].split('/')
        self.script_name = script_name

    def post_check(self):
        request_body_size = int(self.environ.get('CONTENT_LENGTH', 0))
        self.post_data = urlparse.parse_qs(self.environ['wsgi.input'].read(request_body_size))

    def print_home(self):
        self.output.append(u'<h1>A che ora andiamo a mensa?</h1>\n')
        self.output.append(u'Ciao utente <b>@%s</b>!<br>\n' % (self.user.get_pretty_name()))
        self.output.append(u'Queste sono le dichiarazioni per il %s a %s.<br>\n' % (self.phase.date, MOMENTS[self.phase.moment][0]))
        self.output.append(u'<br>\n')
        for statement in self.phase.get_statements():
            self.output.append(u'<b>@%s</b>: %s<br>\n' % (statement.user.get_pretty_name(), statement.value))
        self.output.append(u'<br>\n')
        self.output.append(u'Fai la tua dichiarazione!<br>\n')
        self.output.append(u'<form method="post" action="%s/state">\n' % (self.script_name))
        self.output.append(u'<input type="text" name="statement" value="%s" size="100">\n' % (html_escape(self.user.get_statement(self.phase).value)))
        self.output.append(u'<input type="submit" name="submit" value="Sottometti!">\n')
        self.output.append(u'</form>\n')
        self.output.append(u'<i>Buone patate!</i><br>\n')
        self.output.append(u'<a href="%s/json">JSON</a><br>\n' % (self.script_name))

    def print_debug(self):
        self.content_type = 'text/plain'
        pp = pprint.PrettyPrinter(indent=4)
        self.output.append('URL breakdown: %r\n' % (self.url_breakdown))
        self.output.append(pp.pformat(self.environ))

    def receive_statement(self):
        self.post_check()
        statement = self.user.get_statement(self.phase)
        new_value = self.post_data.get('statement', [])
        if len(new_value) == 0:
            self.session.delete(statement)
        else:
            statement.value = new_value[0].decode('utf-8')
            self.session.add(statement)
        self.redirect(self.script_name)

    def print_json_statements(self):
        self.content_type = 'application/json'
        ret = {'statements': []}
        for statement in self.phase.get_statements():
            ret['statements'].append({'username': statement.user.get_pretty_name(),
                                      'value': statement.value})
        self.output.append(json.dumps(ret))

    # TODO
    def error(self):
        pass

    def redirect(self, where):
        self.status = '302 Found'
        self.response_headers += (('Location', where),)
        self.output = []

    def finish(self):
        self.session.commit()
        self.output = "".join(self.output).encode('utf-8')
        self.response_headers += [('Content-Type', '%s; charset=utf-8' % (self.content_type)),
                                  ('Content-Length', str(sum(map(lambda x: len(x), self.output))))]
        self.start_response(self.status, self.response_headers)

    def __call__(self):
        self.url_check()
        self.user_check()
        self.phase_check()

        if self.url_breakdown == ['json']:
            self.print_json_statements()
        elif self.url_breakdown == ['debug']:
            self.print_debug()
        elif self.url_breakdown == ['state']:
            self.receive_statement()
        else:
            self.print_home()

        self.finish()
        return [self.output]

class MensaApp:

    def __init__(self):
        pass

    def __call__(self, environ, start_response):
        handler = MensaHandler(environ, start_response)
        return handler()

application = MensaApp()
