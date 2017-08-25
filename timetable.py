'''
Created on 17 de abr de 2017

@author: fvj
'''
import requests, datetime, json, sys
from getpass import getpass
from bs4 import BeautifulSoup
from math import floor

DEFAULT_TOTAL_MONTHS = 3

def login(user,passw):
    data_form = {'empresa':'a128879', 'matricula':user, 'senha':passw}
    return requests.post('https://www.ahgora.com.br/externo/login', data_form)

def loginSuccessful(login_data):
    data = json.loads(login_data._content.decode("utf-8"))
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

def getBalanceFromTotals(table):
    return {}

def parseTimetable(table):
    days = []
    for row in table.tbody.find_all('tr'):
        c  = row.contents[1].contents
        if len(c) > 12:
            date = c[0].strip()
            batidas = ''.join(c[3].stripped_strings)
            results = list(s.strip() for s in c[11].strings)
            hours_worked = getHoursWorked(results)
            balance = getBalance(results)
            balance_min = time2mins(balance)
            days.append( {'date':date, 'batidas':batidas, 'hours_worked':hours_worked, 'balance':balance, 'balance_min':balance_min} )
    return days

def getHoursWorked(results):
    for i in results:
        if i.startswith('Horas Trabalhadas: '):
            return i[19:]
    return ''
    
def getBalance(results):
    for i in results:
        if i.startswith('Banco de Horas: '):
            return i[16:]
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

if __name__ == '__main__':
    if len(sys.argv) >= 3:
        u = sys.argv[1]
        p = sys.argv[2]
    else:
        print('Matricula:')
        u = input()
        p = getpass("Senha:\n")
    
    try:
        totalMonths = int(input('Deseja buscar quantos meses? [default={}]\n'.format(DEFAULT_TOTAL_MONTHS)))
    except ValueError:
        totalMonths = DEFAULT_TOTAL_MONTHS
    
    print('Fazendo login...')
    full_data = []
    login_data = login(u,p)
    if not loginSuccessful(login_data):
        print('Login unsuccessful! Terminating..')
        exit(-1)
    session_cookies = login_data.cookies
    
    
    months = ['']
    today = datetime.date.today()
    
    for i in range(totalMonths-1):
        month = (today.month + 10 - i) % 12 + 1
        year = today.year - floor((1 + i - today.month)/12) - 1
        months.append('{:02d}-{:04d}'.format(month, year))
    
    for month in months:
        print('Buscando dados do mes {}...'.format(month if month else 'atual'))
        tables = requestTables(session_cookies, month)
        
        for t in tables:
            if isTotalsTable(t):
                getBalanceFromTotals(t)
            else:
                full_data += parseTimetable(t)
              
    full_data = sorted(full_data, key=getDate)
    
    output_file = open('horarios.csv', 'w')
    output_file.write('Data; Batidas; Horas Trabalhadas; Saldo; Saldo (minutos)\n')
    for entry in full_data:
        output_file.write('{}; {}; {}; {}; {}\n'.format(entry['date'], entry['batidas'], entry['hours_worked'], entry['balance'], entry['balance_min']))
    output_file.close()
    print('Pronto! Arquivo \'horarios.csv\' criado.')