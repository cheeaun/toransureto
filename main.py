#!/usr/bin/env python

import os
import wsgiref.handlers
from cgi import escape
from urllib import urlencode, quote, unquote
from xml.dom.minidom import parseString
from django.utils import simplejson
from google.appengine.api import urlfetch
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

class MainHandler(webapp.RequestHandler):
  def get(self):
    values = {}
    path = os.path.join(os.path.dirname(__file__), 'index.html')
    self.response.out.write(template.render(path, values))

class TranslateHandler(webapp.RequestHandler):
  def get(self):
    q = escape(self.request.get('q'))
    response = {
      'text': q,
      'detectedLanguage': None,
      'japanese': None,
      'romaji': None
    }
    json = ''
    
    params1 = {
      'q': (q + '\n').encode('utf-8'), # stupid newline makes Mr Google more sane.
      'v': '1.0',
      'langpair': '|ja',
      'key': 'ABQIAAAAd-hs0KXlCbCt7FLKomCbWhTCtxzNMneMUp27SV06n9DShlovUxRxc0P9R00OLnmyRoHK0YvXOaQ9PQ'
    }
    url1 = 'http://ajax.googleapis.com/ajax/services/language/translate?' + urlencode(params1)
    
    params2 = {
      'unknown_text': q.encode('utf-8'),
      'text': None,
      'mode': 1
    }
    url2 = 'http://romaji.udp.jp/romaji.cgi'
    
    if q:
      try:
        result = urlfetch.fetch(url1, deadline=10)
        if result.status_code == 200:
          content = simplejson.loads(result.content)
          if content['responseData']:
            response['detectedLanguage'] = content['responseData']['detectedSourceLanguage']
            response['japanese'] = content['responseData']['translatedText']
            
            try:
              params2['text'] = response['japanese'].encode('utf-8')
              result2 = urlfetch.fetch(url2, payload=urlencode(params2), method=urlfetch.POST, headers={'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'}, deadline=10)
              if result2.status_code == 200:
                content = parseString(result2.content)
                text = []
                rts = content.getElementsByTagName('rt')
                for rt in rts:
                  nodelist = rt.childNodes
                  for node in nodelist:
                    if node.nodeType == node.TEXT_NODE and node.data:
                      text += [node.data]
                response['romaji'] = ' '.join(text)
              else:
                self.error(result.status_code)
            except:
              self.error(500)
        else:
          self.error(result.status_code)
      except:
        self.error(500)
    
    json = simplejson.dumps(response, indent=4, ensure_ascii=False)
    self.response.headers['Content-Type'] = 'application/javascript; charset=utf-8'
    self.response.out.write(json)

def main():
  application = webapp.WSGIApplication([
    ('/', MainHandler),
    ('/trans', TranslateHandler)
  ], debug=True)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()
