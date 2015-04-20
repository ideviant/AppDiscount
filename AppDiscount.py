#coding=UTF-8
__author__ = 'Kane'

import urllib2
import json
import poplib
import re
import MySQLdb
import sys
import smtplib
from email.mime.text import MIMEText


reload(sys)
sys.setdefaultencoding('utf-8')

def getContent(appID):
    lookupUrl = 'https://itunes.apple.com/cn/lookup?id={0}'.format(appID)
    try:
        data = urllib2.urlopen(lookupUrl).read()
    except urllib2.URLError,e:
        print "Urlopen failed:",e
    jsonData = json.loads(data)
    if(jsonData['resultCount']):
        results = jsonData[r'results'][0]
        trackName = results['trackName']
        price =  results['price']
        print price
        return trackName, price


def receiveMail():
    try:
        p=poplib.POP3('pop.qq.com')
        p.user('nowiam@qq.com')
        p.pass_('Passwd123')
        ret = p.stat()
    except poplib.error_proto,e:
        print "Login failed:",e
    list=p.list()[1]
    print list[-1:][0]

    appUrl = ''
    userEmail = ''
    infoList = []
    emailNumFile = open('emailNum.txt')
    emailNum = int(emailNumFile.read())
    print emailNum
    emailNumFile.close()

    for item in list[emailNum:]:
        number,octets = item.split(' ')
        print number
        lines=p.retr(number)[1]
        for piece in lines:
            if piece.startswith('https://appsto.re/cn/'):
                appUrl = piece
            if piece.startswith('From: '):
                userEmail = piece[(piece.find('<')+1):(piece.rfind('>'))]
        if(appUrl and userEmail):
            print appUrl
            infoList.append(appUrl+'$$$'+userEmail)
            print 'Get a mail from : ' + userEmail
            appUrl = ''
            userEmail = ''

    emailNumFile = open('emailNum.txt','w')
    emailNum, emailOctets = list[-1:][0].split(' ')
    emailNumFile.write(emailNum)
    print emailNum
    emailNumFile.close()

    print '----------------Receive mail done----------------'
    return infoList

def getAppId(url):
    try:
        data = urllib2.urlopen(url).read()
    except urllib2.URLError,e:
        print "Urlopen failed:",e
    reAppID = u'https://itunes.apple.com/(.*?)l=en&mt=8'
    appID = re.findall(reAppID, data)[0]
    return appID[(appID.rfind(u'/')+3):-1]

def recordData():
    mailLists = list(set(receiveMail()))
    for mail in mailLists:
        appUrl, userEmail = mail.split('$$$')
        print appUrl
        print userEmail
        if(hasRecord(appUrl, userEmail)):
            print userEmail + ' and ' + appUrl + ' has record!'
            continue
        appId = getAppId(appUrl)
        trackName, price = getContent(appId)
        print trackName
        print '¥','%.2f'%price
        storeData(appUrl, appId, userEmail, trackName, price)
        print '------------------------'


def storeData(appUrl, appId, userEmail, trackName, price):
    db=MySQLdb.connect(host='localhost',user='root',passwd='root',db='test')
    cursor = db.cursor()
    sql = 'insert into app values ("{0}","{1}","{2}","{3}","{4}","{5}");'.format(appUrl, appId, userEmail,trackName, price, price)
    print sql
    try:
        cursor.execute(sql)
        db.commit()
    except:
        db.rollback()
    db.close()
    print 'Store data done!'

def readData():
    db=MySQLdb.connect(host='localhost',user='root',passwd='root',db='test')
    cursor = db.cursor()
    cursor.execute("select * from app")
    datas = cursor.fetchall()
    for data in datas:
        print data
    db.close()

def getCurrentPrice(appID):
    lookupUrl = 'https://itunes.apple.com/cn/lookup?id={0}'.format(appID)
    try:
        data = urllib2.urlopen(lookupUrl).read()
        jsonData = json.loads(data)
        results = jsonData[r'results'][0]
        price =  results['price']
        return price
    except urllib2.URLError,e:
        print "Urlopen failed:",e


def updateCurrentPrice(appId, currentPrice):
    db=MySQLdb.connect(host='localhost',user='root',passwd='root',db='test')
    cursor = db.cursor()
#    sql = 'update app set currentPrice="{0}" where appId="{1}"'.format(currentPrice, appId)
    sql = 'update app set currentPrice="{0}" where appId="{1}"'.format(currentPrice, appId)
    cursor.execute(sql)
    db.close()

def updateBasePrice(appId,currentPrice):
    db=MySQLdb.connect(host='localhost',user='root',passwd='root',db='test')
    cursor = db.cursor()
    sql = 'update app set price="{0}" where appId="{1}"'.format(currentPrice, appId)
    cursor.execute(sql)
    db.close()


def updateData():
    db=MySQLdb.connect(host='localhost',user='root',passwd='root',db='test')
    cursor = db.cursor()
    cursor.execute("select * from app")
    datas = cursor.fetchall()
    for data in datas:
        appId = data[1]
        currentPrice = getCurrentPrice(appId)
        updateCurrentPrice(appId, currentPrice)
        print data
    db.close()

def checkDiscount():
    db=MySQLdb.connect(host='localhost',user='root',passwd='root',db='test')
    cursor = db.cursor()
    cursor.execute("select * from app")
    datas = cursor.fetchall()
    for data in datas:
        print data
        if(data[4] > data[5]):
            sendEmail(data[2], '冰点:'+data[3],str(data[0])+ '\n原价:' + str(data[4]) +'\n现价:'+str(data[5]))
            print data[0] + ' Price changes!'
        elif(data[4] < data[5]):
            updateBasePrice(data[1],data[5])
            sendEmail('nowiam@qq.com', '涨价:'+data[3],str(data[0])+ '\n原价:' + str(data[4]) +'\n现价:'+str(data[5]))
            print data[0] + ' Price changes!'
    db.close()

def sendEmail(to, subject, content):
    msg = MIMEText(content,'plain','utf-8')
    msg['Subject'] = subject   #设置主题
    msg['From'] = 'nowiam@qq.com'     #发件人
    msg['To'] = to; #收件人
    try:
        s = smtplib.SMTP()
        s.connect('smtp.qq.com')
        s.login('nowiam','Passwd123')
        s.sendmail('nowiam@qq.com', to, msg.as_string())
        print 'Mail sent to:' + to
        s.close()
    except Exception, e:
        print str(e)

def hasRecord(appUrl, userEmail):
    db=MySQLdb.connect(host='localhost',user='root',passwd='root',db='test')
    cursor = db.cursor()
    sql = 'select COUNT(*) from app where appUrl="{0}" and userEmail="{1}"'.format(appUrl, userEmail)
    cursor.execute(sql)
    datas = cursor.fetchall()
    if(datas[0][0]):
        return True
    db.close()

recordData()
updateData()
#readData()
checkDiscount()