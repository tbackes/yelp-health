import pandas as pd
import numpy as np
import pickle
import requests

from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from cStringIO import StringIO

from urllib2 import urlopen, Request
from StringIO import StringIO as sIO
import re
from sys import argv

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
                #print '%04d is valid' % (j+1)
                pdfs['%s%04d' % (base, j+1)] = {'link': link, 'text': convert_pdf_to_txt(link)}
            else:
                break
        print '%s max: %d' % (base, j)
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

def get_restaurant_details(pdf):
    '''
    Extract restaurant details from a pdf that has been converted to text

    INPUT:  pdf = str, text of a health inspection pdf 
    OUTPUT: d = dict, restaurant/inspection information (i.e., name, address, date, etc)
    '''
    # split text by line
    t = pdf.split('\n')

    # get index of certain fields that can be used to locate desired information
    f = t.index('Food Safety Assessment Categories:')
    n = t.index('Client Name:')
    z = t.index('Zip:')
    p = t.index('Priority Code:')
    
    if t[f+2] == 'Client Name:':
        f += 1
    
    # get index of priority status (only valid values are 1, 2, & H)
    i1 = t.index('1')
    i2 = t.index('2')
    if 'H' in t:
        i_priority = min([i1,i2,t.index('H')])
    else:
        i_priority = min([i1,i2])
    
    d =    {'client_id': t[f+2],
            'address': t[f+3],
            'city': t[f+4],
            'municipality': t[f+5],
            'category': t[f+6],
            'reinspection': t[f+7],
            'name': t[n + 2],
            'zip': t[z - 2],
            'inspector': t[z + 1],
            'date': t[p + 2],
            'purpose': t[p + 3],
            'priority': t[i_priority]}
    
    # Check for several known exceptions in field order:
    if d['name'] == 'State:':
        d['name'] = t[t.index('Inspector:') + 2]
        
    if is_number(d['inspector']):
        d['inspector'] = t[z + 2]
        d['zip'] = t[z + 1]
        
    if d['zip'] == 'Priority Code:':
        if t[p+8] == '':
            d['zip'] = t[z+3]
            d['date'] = t[t.index('Inspection Date:') + 1]
        else:
            d['zip'] = t[p + 8]
            d['date'] = t[p + 5]
        d['purpose'] = t[p + 6]
        
    if len(d['date']) == 5 and is_number(d['date']):
        i = t.index('Inspection Date:')
        d['date'] = t[i - 3]
        d['purpose'] = t[i - 2]
    elif len(d['date']) < 6:
        d['date'] = t[t.index('Inspection Date:') + 1]
        
    if len(d['purpose']) < 1:
        d['purpose'] = t[t.index('Purpose:') + 1]
    
    if t[f+1] == 'Client Name:':
        d['name'] = t[t.index('Inspector:')+4]
    
    if d['city'] == 'Zip:':
        r = t.index('Re- Inspection Date:')
        d['city'] = t[f+5]
        d['municipality'] = t[f+7]
        d['category'] = t[f+8]
        d['reinspection'] = t[f+9]
        d['name'] = t[r+2]
        d['zip'] = t[r+4]
        d['inspector'] = t[f+6]
    elif d['city'] == 'State:':
        d['city'] = t[f+6]
        d['municipality'] = t[f+8]
        d['category'] = t[f+9]
        d['reinspection'] = t[f+10]
        
    return d

    
def get_violation_details(pdf):
    '''
    Extract inspection details from a pdf that has been converted to text

    INPUT:  pdf = str, text of a health inspection pdf 
    OUTPUT: d = dict, violation information (codes for critical and noncritical violations)
    '''
    # first isolate lines that are focused on violation summaries and clean up spacing
    # the following labels get interspersed through the violation info (unpredictably)
    # by the pdf-to-text parser, so they should be cleaned up for easier processing
    v =  pdf.split('Inspection Details')[1]\
            .replace('\n\nViolation:\nComments:\nFood Code Section(s):\nCorrective Action:\n\n','\n\n')\
            .replace('Corrective Action:\n\n','\n\n')\
            .replace('\nOther Assesment observations and comments:\n\n','\n\n')\
            .replace('Non Critical Violations:','Non Critical Violations:\n')\
            .replace('\n3','\n\n3')\
            .replace('\n 3','\n\n3')\
            .replace('\n3\n','3\n')\
            .replace('\n\n\n','\n\n')\
            .replace('\n\n\n','\n\n')\
            .split('\n\n')
            
    # critical violations are identified by a 1-2 code appearing on it's own line
    critical = [int(x) for x in v if (is_number(x) and len(x) < 4)]
    noncritical = []
    
    # non-critical violations are identified by a 3 digit number (in the 300s)
    # all non-critical violations appear after the 'Non Critical Violations' header
    if 'Non Critical Violations:' in v:
        ind_nc = v.index('Non Critical Violations:')+1
        ind_stop = len(v)
        pattern = re.compile('\b?3\d\d\b?')
        # find all numbers in the 300s, be sure to exclude date tags and the address
        # they should be excluded anyways, but I'm explicitly checking just in case
        temp = [pattern.findall(re.sub('\d{12}','',x)) for x in v[ind_nc:ind_stop] if re.search('3901 Penn Ave', x) is None]
        
        pattern = re.compile('3\d\d')
        noncritical = [int(x[0]) for x in temp if len(x) > 0]

    return {'critical':critical, 'noncritical':noncritical}

if __name__ == '__main__':
    '''
    f_list = ['20110101','20110111','20110112','20110214','20110221','20110228','20110302',
              '20110303','20110310','20110317','20110324','20110331','20110407','20110414',
              '20110421','20110428','20110505','20110512','20110519','20110526']
    d = read_in_dicts(f_list)
    save_pdf_text(d, '../data/pitt/pitt_%s_to_%s.pkl' % ('20110101', '20110601'))
    '''
    start = pd.datetime(2011,6,16)
    if len(argv) > 1:
        start = pd.datetime(int(argv[1]),int(argv[2]),int(argv[3]))
    delta = pd.Timedelta(1, 'd')
    step_size = 7
    n_loops = 24

    for i in xrange(n_loops):
        print '[%02d] START: %s' % (i, start.strftime("%Y%m%d"))
        pdfs = get_pdf_text(start, step_size)
        save_pdf_text(pdfs, '../data/pitt/pitt_%s.pkl' % start.strftime("%Y%m%d"))
        start += step_size * delta

