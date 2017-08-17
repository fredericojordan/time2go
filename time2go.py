'''
Created on 17 de abr de 2017

@author: fvj
'''
import requests, datetime, sys
from json import loads
from getpass import getpass
from bs4 import BeautifulSoup
from math import floor

def login(user,passw):
    data_form = {'empresa':'a128879', 'matricula':user, 'senha':passw}
    return requests.post('https://www.ahgora.com.br/externo/login', data_form)

def loginSuccessful(login_data):
    data = loads(login_data._content.decode("utf-8"))
    if 'r' in data and data['r'] == 'error':
        return False
    return True

def requestTables(cookies, month=''):
    response = requests.get('https://www.ahgora.com.br/externo/batidas/'+month, cookies=cookies)
    page_soup = BeautifulSoup(response._content, 'html.parser')
    tables = page_soup.find_all('table', class_="table table-bordered table-striped")
    return tables

def isTotalsTable(table):
    return table.has_attr('id')

def calculateLeavingTime(entries, balance):
    last_entry = entries.split()[-1]
    d1 = datetime.datetime.strptime(last_entry, "%H:%M")
    d2 = datetime.datetime.strptime(balance.lstrip("-"), "%H:%M")
    dt1 = datetime.timedelta(hours=d1.hour, minutes=d1.minute)
    dt2 = datetime.timedelta(hours=d2.hour, minutes=d2.minute)
    f = dt1 + dt2
    hours = floor(f.seconds/3600)
    minutes = floor(f.seconds%3600/60)
    
    if (len(entries.split()) < 2):
        hours += 1
                    
    return '{:02d}:{:02d}'.format(hours, minutes)
    

def parseLeavingTime(today, table):
    for row in table.tbody.find_all('tr'):
        c  = row.contents[1].contents
        if len(c) > 12:
            date = c[0].strip()
            if date == '{:02d}/{:02d}/{:04d}'.format(today.day, today.month, today.year):
                batidas = ''.join(c[3].stripped_strings)
                results = list(s.strip() for s in c[11].strings)
                balance = getBalance(results)
                
                if len(batidas.split())%2 == 0:
                    print('Voce nao esta em horario de trabalho! Seu saldo de hoje: {}.'.format(balance))
                    return
                
                print('Voce pode ir para casa as {}{}'.format(calculateLeavingTime(batidas, balance), ' (1h de almoco)' if len(batidas.split()) < 2 else ''))
                return
    
def getBalance(results):
    for i in results:
        if i.startswith('Banco de Horas: '):
            return i[16:]
    return ''

def getBalanceFromTotals(table):
    for row in table.tbody.find_all('tr'):
        if row.contents[1].contents[0] == 'SALDO':
            return row.contents[3].string.strip()
    return 0

def getDailyBalanceFromTimetable(table):
    for row in table.tbody.find_all('tr'):
        c  = row.contents[1].contents
        if len(c) > 12:
            date = c[0].strip()
            
            today = datetime.date.today()
            today = '{:02d}/{:02d}/{:04d}'.format(today.day, today.month, today.year)
            
            if date == today:
                results = list(s.strip() for s in c[11].strings)
                return getBalance(results)
    return 0

def getHoursWorked(results):
    for i in results:
        if i.startswith('Horas Trabalhadas: '):
            return i[19:]
    return ''

def time2mins(time_str):
    nums = time_str.split(':')
    if len(nums) >= 2:
        hours = int(nums[0])
        mins = int(nums[1])
        return 60*hours - mins if time_str.startswith('-') else 60*hours + mins 
    else:
        return 0

def getDate(item):
    return datetime.datetime.strptime(item['date'], '%d/%m/%Y')
    
def parseYesterdayBalance(balance, daily_balance):
    balance_n = False
    daily_balance_n = False
    
    if balance.startswith('-'):
        balance_n = True
        balance = balance.strip('-')
        
    if daily_balance.startswith('-'):
        daily_balance_n = True
        daily_balance = daily_balance.strip('-')
    
    balance = datetime.datetime.strptime(balance, "%H:%M")
    daily_balance = datetime.datetime.strptime(daily_balance, "%H:%M")
    
    if balance_n ^ daily_balance_n:
        balance += datetime.timedelta(hours=daily_balance.hour, minutes=daily_balance.minute)
        balance = balance.strftime("%H:%M")
        if balance_n:
            balance = '-' + balance
    else:
        if (balance - daily_balance) < datetime.timedelta(minutes=0):
            balance = daily_balance - datetime.timedelta(hours=balance.hour, minutes=balance.minute)
            
            balance = balance.strftime("%H:%M")
            if not balance_n:
                balance = '-' + balance
        else:
            balance -= datetime.timedelta(hours=daily_balance.hour, minutes=daily_balance.minute)
            
            balance = balance.strftime("%H:%M")
            if balance_n:
                balance = '-' + balance
    return balance

if __name__ == '__main__':
    if len(sys.argv) >= 3:
        u = sys.argv[1]
        p = sys.argv[2]
    else:
        print('Matricula:')
        u = input()
        p = getpass("Senha:\n")
    
    print('Fazendo login...')
    login_data = login(u,p)
    if not loginSuccessful(login_data):
        print('Login unsuccessful! Terminating..')
        exit(-1)
    session_cookies = login_data.cookies
     
    today = datetime.date.today()
    month = '{:02d}-{:04d}'.format(today.month if today.day < 26 else today.month+1, today.year) # nao funciona entre o natal e o ano novo. nao consiste bug, pois o programa nao deve rodar nesses dias.
     
    print('Buscando dados...')
    tables = requestTables(session_cookies, month)
     
    for t in tables:
        if isTotalsTable(t):
            balance = getBalanceFromTotals(t)
        else:
            daily_balance = getDailyBalanceFromTimetable(t)
    
    print('Saldo do banco de horas: ' + parseYesterdayBalance(balance, daily_balance))
    parseLeavingTime(today, t)
    print('Aperte [ENTER] para sair...')
    input()