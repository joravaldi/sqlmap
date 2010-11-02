#!/usr/bin/env python

"""
$Id$

Copyright (c) 2006-2010 sqlmap developers (http://sqlmap.sourceforge.net/)
See the file 'doc/COPYING' for copying permission
"""

import re

from lib.core.common import getFilteredPageContent
from lib.core.common import preparePageForLineComparison
from lib.core.common import wasLastRequestError
from lib.core.data import conf
from lib.core.data import kb
from lib.core.data import logger
from lib.core.session import setMatchRatio

def comparison(page, headers=None, getSeqMatcher=False, pageLength=None):
    regExpResults = None

    # String to be excluded before calculating page hash
    if conf.eString and conf.eString in page:
        index              = page.index(conf.eString)
        length             = len(conf.eString)
        pageWithoutString  = page[:index]
        pageWithoutString += page[index+length:]
        page               = pageWithoutString

    # Regular expression matches to be excluded before calculating page hash
    if conf.eRegexp:
        regExpResults = re.findall(conf.eRegexp, page, re.I | re.M)

        if regExpResults:
            for regExpResult in regExpResults:
                index              = page.index(regExpResult)
                length             = len(regExpResult)
                pageWithoutRegExp  = page[:index]
                pageWithoutRegExp += page[index+length:]
                page               = pageWithoutRegExp

    # String to match in page when the query is valid
    if conf.string:
        return conf.string in page

    # Regular expression to match in page when the query is valid
    if conf.regexp:
        return re.search(conf.regexp, page, re.I | re.M) is not None

    # Dynamic content lines to be excluded before calculating page hash
    for item in kb.dynamicMarkings:
        prefix, postfix = item
        if prefix is None:
            page = re.sub('(?s)^.+%s' % postfix, postfix, page)
        elif postfix is None:
            page = re.sub('(?s)%s.+$' % prefix, prefix, page)
        else:
            page = re.sub('(?s)%s.+%s' % (prefix, postfix), '%s%s' % (prefix, postfix), page)

    if kb.data.seqLock:
        kb.data.seqLock.acquire()

    if not conf.eRegexp and not conf.eString and kb.nullConnection:
        ratio = 1. * pageLength / len(conf.seqMatcher.a)
        if ratio > 1.:
            ratio = 1. / ratio
    else:
        conf.seqMatcher.set_seq2(page if not conf.textOnly else getFilteredPageContent(page))
        ratio = round(conf.seqMatcher.ratio(), 3)

    if kb.data.seqLock:
        kb.data.seqLock.release()

    # If the url is stable and we did not set yet the match ratio and the
    # current injected value changes the url page content
    if conf.matchRatio is None:
        if conf.thold:
            conf.matchRatio = conf.thold

        elif kb.pageStable and ratio > 0.6 and ratio < 1:
            logger.debug("setting match ratio to %.3f" % ratio)
            conf.matchRatio = ratio

        elif not kb.pageStable or ( kb.pageStable and ratio < 0.6 ):
            logger.debug("setting match ratio to default value 0.900")
            conf.matchRatio = 0.900

        if conf.matchRatio is not None:
            setMatchRatio()

    # If it has been requested to return the ratio and not a comparison
    # response
    if getSeqMatcher:
        return ratio

    # In case of an DBMS error page return False
    elif wasLastRequestError():
        return False

    # If the url is not stable it returns sequence matcher between the
    # first untouched HTTP response page content and this content
    else:
        return ratio > conf.matchRatio
