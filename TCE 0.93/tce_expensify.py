import requests
import json
import pandas as pd
import re

def capture(x):
    if x:
        res = re.search(pattern = '[A-Z]{7}[0-9]{2}', string = x)
        if res: return res.group()
        else: return None
    else: return None

def amountFixer(x):
    if not(isNan(x[1])): return x[1]
    else: return x[0]

def isNan(x):
    return x != x

def expense_file_exporter(endpoint, api_id, api_secret, template):
    JobDescription_exporter = {
    "requestJobDescription": json.dumps({
        "type":"file",
        "credentials": {
            "partnerUserID": api_id,
            "partnerUserSecret": api_secret
        },
        "onReceive":{
                "immediateResponse":["returnRandomFileName"]
        },
        "inputSettings":{
            "type":"combinedReportData",
            "reportState":"REIMBURSED",
            "limit":"10000",
            "filters":{
                "startDate":"2021-08-01",
                "endDate": "2022-05-20"
                 }
        },
        "outputSettings":{
            "fileExtension":"csv"
        }
    }),
    "template": template
    }
    response = requests.post(endpoint, data=JobDescription_exporter)
    return response

def expense_file_downloader(endpoint, api_id, api_secret, fileName):
    JobDescription_downloader = {"requestJobDescription": json.dumps({
        "type":"download",
        "credentials": {
            "partnerUserID": api_id,
            "partnerUserSecret": api_secret
        },
        "fileName": fileName,
        "fileSystem":"intergrationServer"
        })
    }

    response = requests.post(endpoint, data=JobDescription_downloader)
    response = response.text.split('\n')
    expense_records = [ i.split('\|/') for i in response[1:]]
    col_names = response[0].split(',')

    return expense_records, col_names

#----------------------------------------------------------------------------------------------

endpoint = "https://integrations.expensify.com/Integration-Server/ExpensifyIntegrations"

template = """<#if addHeader == true>
    Merchant,Amount,M_Amount,Type,Description,Date<#lt>
</#if>
<#list reports as report>
    <#list report.transactionList as expense>
        ${expense.merchant}\|/<#t>
        <#-- note: expense.amount prints the original amount only -->
        ${expense.amount}\|/<#t>
        ${expense.modifiedAmount}\|/<#t>
        ${expense.category}\|/<#t>
        ${expense.comment}\|/<#t>
        ${expense.created}<#lt>
    </#list>
</#list>"""


oid = "blurp"
osecret = "blurrrp"

def get_expensify(proj_id):
    response = expense_file_exporter(endpoint, oid, osecret, template)
    fileName = response.text

    expense_records, col_names = expense_file_downloader(endpoint, oid, osecret, fileName)


    df = pd.DataFrame(data = expense_records, columns = col_names)

    df['JIRA_ID'] = df['Description'].apply(capture)
    df['Amount'] = df['Amount'].apply(lambda x: int(x)/100 if x else 0)
    df['M_Amount'] = df['M_Amount'].apply(lambda x: int(x)/100 if x else None)
    #df['Date'] = pd.to_datetime(df['Date'])
    df['F_Amount'] = df[['Amount', 'M_Amount']].apply(amountFixer, axis=1)


    return df[df['JIRA_ID'] == proj_id]

if __name__ == '__main__':
    import time
    proj_id = input('Enter a Project ID :- ')
    start = time.perf_counter()
    print(get_expensify(proj_id))
    print('Time till result : ', time.perf_counter() - start)
    