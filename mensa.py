import pprint

def application(environ, start_response):
    status = '200 OK' 
    try:
        username = environ['REMOTE_USER']
    except KeyError:
        output = 'Unauthenticated user!'
    else:
        output = 'Hello World! (and especially hello %s)' % (username)

    pp = pprint.PrettyPrinter(indent=4)
    output += '\n' + (pp.pformat(environ))

    response_headers = [('Content-type', 'text/plain'),
                        ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]
