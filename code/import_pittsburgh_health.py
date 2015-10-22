import pandas as pd
import numpy as np
import pickle

from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from cStringIO import StringIO

from urllib2 import urlopen, Request
from StringIO import StringIO as sIO
import re

def url_to_pdf(url):
    '''Treat give url as a pdf, to be fed into pdfminer functions'''
    open = urlopen(Request(url)).read()
    return sIO(open)

def convert_pdf_to_txt(path):
    '''Convert pdf at provided url to a string'''
    rsrcmgr = PDFResourceManager()
    retstr = StringIO()
    codec = 'utf-8'
    laparams = LAParams()
    device = TextConverter(rsrcmgr, retstr, codec=codec, laparams=laparams)
    #fp = file(path, 'rb')
    fp = url_to_pdf(path)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    password = ""
    maxpages = 0
    caching = True
    pagenos=set()
    pagenos=set()
    for i, page in enumerate(PDFPage.get_pages(fp, pagenos, maxpages=maxpages, password=password,caching=caching, check_extractable=True)):
        #if i > 0:
        interpreter.process_page(page)
    fp.close()
    device.close()
    str = retstr.getvalue()
    retstr.close()
    return str

def get_pdf_text(start, n_days):
    '''
    Get pdf text for n_days starting at the given date
    
    INPUT:  start = pd.datetime, first date to check 
            n_days = int, number of days to check
    OUTPUT: pdfs = dict, {date str: {link:, pdf text:}}
    
    There are up to ~75 restaurants reported per day, so this function looks at up to 100 pdf links
    for each day (links end in 0001 through 0100). The first link that does not return a pdf causes
    the loop to break and continue the search starting on the next day.
    
    It looks like pdfs are only present on weekdays, but I didn't want to accidentally overlook any results
    so this function checks all days. Only days with pdfs are included in the returned dictionary.
    '''
    delta = pd.Timedelta(1, 'd')
    pdfs = {}
    for i in xrange(n_days):
        base = (start + i*delta).strftime("%Y%m%d")
        for j in xrange(100):
            link = 'http://appsrv.achd.net/reports/rwservlet?food_rep_insp&P_ENCOUNTER=%s%04d' % (base,j+1)
            z = requests.get(link)
            if z.headers['Content-Type'] == 'application/pdf':
                pdfs['%s%04d' % (base, j+1)] = {'link': link, 'text': convert_pdf_to_txt(link)}
            else:
                print '%s max: %d' % (base, j)
                break
    return pdfs

def save_pdf_text(pdfs, fname):
    '''Save a dictionary (or other python data structure) at the given pickle file'''
    with open(fname, 'wb') as handle:
        pickle.dump(pdfs, handle)


def merge_two_dicts(x, y):
    '''Given two dicts, merge them into a new dict as a shallow copy.'''
    z = x.copy()
    z.update(y)
    return z

def pull_date_dicts(y, m, d, step_size, n_loops):
    '''
    Save dictionaries of pittsburgh inspection pdf text for given date range
    
    INPUT:  y, m, d = ints, date to start loop
            step_size = number of days to include in each sub_file
            n_loops = number of files to create
    OUTPUT: pdf_main = dict, pdf text from all dates.
    
            intermediate dicts from each loop are pickled
            pdf_main is also pickled
    
    The date range is broken into chunks by step_size and n_loops, to ensure that data
    is incrementally saved (in case of connection failure or some other terminal error).
    '''
    start = pd.datetime(y, m, d)
    delta = pd.Timedelta(1, 'd')
    
    pdf_main = {}
    for i in xrange(n_loops):
        print '[%02d] START: %s' % (i, start.strftime("%Y%m%d"))
        pdfs = get_pdf_text(start, step_size)
        save_pdf_text(pdfs, '../data/pitt/pitt_%s.pkl' % start.strftime("%Y%m%d"))
        pdf_main = merge_two_dicts(pdf_main, pdfs)
        start += step_size * delta
    
    started = pd.datetime(y, m, d)
    ended = start - delta
    save_pdf_text(pdf_main, '../data/pitt/pitt_FULL_%s_to_%s.pkl' % (started.strftime("%Y%m%d"), ended.strftime("%Y%m%d")))
    
    return pdf_main

def read_in_dicts(f_list):
    '''
    Read in saved dictionaries and merge into a final dictionary.
    
    INPUT:  list, strings to be inserted in path: ..data/pitt/pitt_$XXX$.pkl
    OUTPUT: merged dictionary, aggregated over all input files
    '''
    f_path = '../data/pitt/pitt'
    d = {}
    for f in f_list:
        d = merge_two_dicts(d, pickle.load(open('%s_%s.pkl' % (f_path,f))))
    return d
