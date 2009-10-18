#!/usr/bin/env python

import os
import wsgiref.handlers
from cgi import escape
from re import compile
from urllib import urlencode
from django.utils import simplejson
from google.appengine.api import urlfetch
from google.appengine.api import memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from BeautifulSoup import BeautifulSoup, SoupStrainer

LANGUAGES = [
  {'code': '', 'lang': 'Detect language'},
  {'code': 'af', 'lang': 'Afrikaans'},
  {'code': 'sq', 'lang': 'Albanian'},
  {'code': 'ar', 'lang': 'Arabic'},
  {'code': 'be', 'lang': 'Belarusian'},
  {'code': 'bg', 'lang': 'Bulgarian'},
  {'code': 'ca', 'lang': 'Catalan'},
  {'code': 'zh-CN', 'lang': 'Chinese'},
  {'code': 'hr', 'lang': 'Croatian'},
  {'code': 'cs', 'lang': 'Czech'},
  {'code': 'da', 'lang': 'Danish'},
  {'code': 'nl', 'lang': 'Dutch'},
  {'code': 'en', 'lang': 'English'},
  {'code': 'et', 'lang': 'Estonian'},
  {'code': 'tl', 'lang': 'Filipino'},
  {'code': 'fi', 'lang': 'Finnish'},
  {'code': 'fr', 'lang': 'French'},
  {'code': 'gl', 'lang': 'Galician'},
  {'code': 'de', 'lang': 'German'},
  {'code': 'el', 'lang': 'Greek'},
  {'code': 'iw', 'lang': 'Hebrew'},
  {'code': 'hi', 'lang': 'Hindi'},
  {'code': 'hu', 'lang': 'Hungarian'},
  {'code': 'is', 'lang': 'Icelandic'},
  {'code': 'id', 'lang': 'Indonesian'},
  {'code': 'ga', 'lang': 'Irish'},
  {'code': 'it', 'lang': 'Italian'},
  {'code': 'ja', 'lang': 'Japanese'},
  {'code': 'ko', 'lang': 'Korean'},
  {'code': 'lv', 'lang': 'Latvian'},
  {'code': 'lt', 'lang': 'Lithuanian'},
  {'code': 'mk', 'lang': 'Macedonian'},
  {'code': 'ms', 'lang': 'Malay'},
  {'code': 'mt', 'lang': 'Maltese'},
  {'code': 'no', 'lang': 'Norwegian'},
  {'code': 'fa', 'lang': 'Persian'},
  {'code': 'pl', 'lang': 'Polish'},
  {'code': 'pt', 'lang': 'Portuguese'},
  {'code': 'ro', 'lang': 'Romanian'},
  {'code': 'ru', 'lang': 'Russian'},
  {'code': 'sr', 'lang': 'Serbian'},
  {'code': 'sk', 'lang': 'Slovak'},
  {'code': 'sl', 'lang': 'Slovenian'},
  {'code': 'es', 'lang': 'Spanish'},
  {'code': 'sw', 'lang': 'Swahili'},
  {'code': 'sv', 'lang': 'Swedish'},
  {'code': 'th', 'lang': 'Thai'},
  {'code': 'tr', 'lang': 'Turkish'},
  {'code': 'uk', 'lang': 'Ukrainian'},
  {'code': 'vi', 'lang': 'Vietnamese'},
  {'code': 'cy', 'lang': 'Welsh'},
  {'code': 'yi', 'lang': 'Yiddish'}
]

class MainHandler(webapp.RequestHandler):
  def get(self):
    values = {'languages': LANGUAGES}
    path = os.path.join(os.path.dirname(__file__), 'index.html')
    self.response.out.write(template.render(path, values))

class TranslateHandler(webapp.RequestHandler):
  def get(self):
    q = escape(self.request.get('q'))
    lang = escape(self.request.get('lang'))
    callback = escape(self.request.get('callback'))
    
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
      'langpair': lang + '|ja',
      'key': 'ABQIAAAAd-hs0KXlCbCt7FLKomCbWhTCtxzNMneMUp27SV06n9DShlovUxRxc0P9R00OLnmyRoHK0YvXOaQ9PQ'
    }
    url1 = 'http://ajax.googleapis.com/ajax/services/language/translate?' + urlencode(params1)
    
    params2 = {
      'type': 'romaji'
    }
    url2 = 'http://tatoeba.org/eng/tools/kakasi?'
    
    if q:
      if not lang: lang = 'auto' # make sure 'q' won't have same value as 'lang'
      json = memcache.get(lang + q)
      
      if json is None:
        try:
          result = urlfetch.fetch(url1, deadline=10)
          if result.status_code == 200:
            content = simplejson.loads(result.content)
            if content['responseData'] and content['responseStatus'] is 200:
              try:
                response['detectedLanguage'] = content['responseData']['detectedSourceLanguage']
              except:
                pass
              response['japanese'] = content['responseData']['translatedText']
              
              try:
                params2['query'] = response['japanese'].encode('utf-8')
                result2 = urlfetch.fetch(url2 + urlencode(params2), allow_truncated=True, deadline=10)
                if result2.status_code == 200:
                  stainer = SoupStrainer(id='conversion')
                  soup = BeautifulSoup(result2.content, parseOnlyThese=stainer)
                  text = soup.contents[0].string.replace('\n', '').strip()
                  response['romaji'] = text
                  
                  json = simplejson.dumps(response, indent=4, ensure_ascii=False)
                  memcache.add(lang + q, json, 86400) # 1 day
                  
                else:
                  self.error(result.status_code)
              except:
                self.error(500)
            else:
              self.error(content['responseStatus'])
          else:
            self.error(result.status_code)
        except:
          self.error(500)

      if callback:
        exp = compile('^[A-Za-z_$][A-Za-z0-9_$]*?$')
        match = exp.match(callback)
        if match: json = callback + '(' + json + ')'
    
      self.response.headers['Content-Type'] = 'application/javascript; charset=utf-8'
      self.response.out.write(json)
      
    else:
      self.redirect('/')
      
  def post(self):
    self.get()

def main():
  application = webapp.WSGIApplication([
    ('/', MainHandler),
    ('/trans', TranslateHandler)
  ], debug=True)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()
