from tce_expensify import get_expensify
from tabulate import tabulate
import json
import pandas as pd
from os import system
from datetime import datetime


class TCEJIRA(object):
    def __init__(self, jiraserver, auth):
        from jira import JIRA
        from tempoapiclient.client import Tempo

        self.jira = JIRA(server=jiraserver, basic_auth=auth)
        self.tempo = Tempo(auth_token="blurrrp",base_url="https://api.tempo.io/core/3")

    # Project Query Function
    def queryProj(self, projectkey=None):
        if projectkey == None:
            print('\n\n Error: Please Enter a Project Key.')
            return None
        else:
            try:
                project = self.jira.project(projectkey)
            except:
                print('\n\n Error: Enter a Valid Project Key or Check Internet Connection.')
                project = None   
            return project
        
    # Project and Issue Query Function, uses the queryProj() Function.
    def queryWorkLogs(self, projectkey=None):
        if projectkey == None:
            print('\n\n Error: Please Enter a Project Key.')
            return None
        project = self.queryProj(projectkey)
        if project == None:
            return [None, None]
        else:
            try:
                worklogs = self.tempo.get_worklogs(dateFrom="2018-01-01",dateTo=datetime.today().strftime('%Y-%m-%d'), projectKey=projectkey)
                #worklogs = self.tempo.get_worklogs(dateFrom="2018-01-01",dateTo="2022-05-20", projectKey=projectkey)
                proj_logs = [project, worklogs]
            except:
                print("\n\n Error: Check Internet Connection or Try Again.")
                worklogs = None
                proj_logs = [project, worklogs]
        return proj_logs

#-----------------Usefull Functions-------------------------------------------------------------------

def fileSelector():
    from math import isnan
    valuefixer = y = lambda _ : _ if ((type(_) == int) or (type(_) == float) and not(isnan(_))) else 0
    
    try:
        job_tracking = pd.read_excel('../TCE-Settings/TCE-Job_Tracking_Sheet.xlsx', sheet_name="Job Tracking")
        job_tracking.drop(index=[len(job_tracking)-1], axis=0, inplace=True)
        job_tracking[['IN JIRA', 'TOTAL PROPOSAL AMOUNT ']]
        job_tracking['TOTAL PROPOSAL AMOUNT '] = job_tracking['TOTAL PROPOSAL AMOUNT '].apply(valuefixer)
    except:
        print(' Error: TCE-Job_Tracking_Sheet.xlsx Not Found.')
        return None
    
    return job_tracking

#       -------------------------------------
def empWiseTimeCalc(logs = None):
    '''Add Docstring'''
    if not(logs):
        return 0
    
    data = [[log['author']['displayName'], log['author']['accountId'], log['issue']['key'], log['timeSpentSeconds']] for log in logs]
    
    df_logs = pd.DataFrame(data=data, columns=['Name', 'AccountId', 'IssueKey', 'Time'])
    
    return df_logs






#       -------------------------------------
def profitCalculator(empwiseTime, proposalamount = None, hourlyRates={"others": [35, '']}):
    if type(empwiseTime) != int:
        forname = empwiseTime
        empwiseTime = empwiseTime.groupby(by='AccountId').sum()['Time']/3600

        df = pd.DataFrame(data = empwiseTime.keys(), columns=['AccountId'])
        df['Name'] = ''
        df['Amount Due'] = 0
        df['HourlyRate'] = 35
        df['Hours'] = 0
        for key in empwiseTime.keys():
            if key in hourlyRates.keys():
                df.loc[df['AccountId'] == key, 'Name'] = forname[forname['AccountId']==key].iloc[0]['Name']
                df.loc[df['AccountId'] == key, 'Hours'] = empwiseTime[key]
                df.loc[df['AccountId'] == key, 'HourlyRate'] = hourlyRates[key][0]
                df.loc[df['AccountId'] == key, 'Amount Due']= empwiseTime[key] * hourlyRates[key][0]
            else:
                df.loc[df['AccountId'] == key, 'Name'] = forname[forname['AccountId']==key].iloc[0]['Name']
                df.loc[df['AccountId'] == key, 'Hours'] = empwiseTime[key]
                df.loc[df['AccountId'] == key, 'HourlyRate'] = hourlyRates['others'][0]
                df.loc[df['AccountId'] == key, 'Amount Due'] = empwiseTime[key] * hourlyRates['others'][0]

        total_expense = sum(df['Amount Due'])
        return (proposalamount - total_expense), total_expense, df #Profit, employee_cost
    else:
        return proposalamount, 0, empwiseTime




# --Display--------------------------------------------------------------------------------------------------
def display():
        inp = ''
        
        print(' Connecting with JIRA ----- Please Wait')
        jira = TCEJIRA(jiraserver='https://compayname.atlassian.net/', auth=('blurrp@gmail.com', 'blurrrp'))
        jobs = fileSelector()
        if type(jobs) == type(None):
            return 0
        try:
            tce_file = open('../TCE-settings/tce-settings.json', 'r')
            tce_settings = json.load(tce_file)
            tce_file.close()
        except:
            print(' Error: TCE-Settings.json Not Found.')
            return 0




        while 1:
            system('cls')
            print()
            print(' ---- Tower Consulting Engineers ----')
            print('\n\n Enter JIRA Project ID')
            inp = input(' ID: ')
            if inp == '-1':
                break
            
            print('\n -  Fetching Data from JIRA')
            proj_logs = jira.queryWorkLogs(inp)
            if proj_logs[0] != None:        
                print(' -- Fetching Data from Expensify')
                df_expenses = get_expensify(inp)
                system('cls')
                print()
                print(' ---- Tower Consulting Engineers ----')
                print('\n Project ID: ', inp)
                print(' Project:    ', proj_logs[0].name)
                print(' Lead:       ', proj_logs[0].lead.displayName)
                print(' ---------------------------------------------------')
                #Getting Proposal Amount from the file, calculating total project time and finding profit.
                try:
                    proposalamount = int(jobs[jobs['IN JIRA'] == inp]['TOTAL PROPOSAL AMOUNT '])
                except:
                    print(' "Proposal Amount for this project is not listed in the excel sheet."')
                    print(' ---------------------------------------------------')
                    proposalamount = 0
                empwiseTime = empWiseTimeCalc(proj_logs[1])
                profit, employee_cost, ammountDue = profitCalculator(empwiseTime, 
                                                                      proposalamount,
                                                                      tce_settings['hourlyRate'])
                expenses_expensify = df_expenses['F_Amount'].sum()
                profit -= expenses_expensify
                if type(empwiseTime) != int:
                    totalTime = sum(ammountDue['Hours'])
                else: totalTime = 0

                table = [['Total Time Logged (JIRA)', f'{totalTime:.2f} Hrs'],
                         ['Total Work Logs', len(proj_logs[1])],
                         ['-----------------------','-------'],
                         ['Total Employee Dues', f'{employee_cost:,.2f}'],
                         ['# of Expenses on Expensify', len(df_expenses)],
                         ['Sum of Expenses', f'{expenses_expensify:,.2f}'],
                         ['Total Expenses', f'{employee_cost+expenses_expensify:,.2f}'],
                         ['-----------------------','-------'],
                         ['Proposal Amount', f'{proposalamount:,}'],
                         ['Profit', f'{profit:,.2f}']]
                print(" Profit Expense Overview")
                print(' ---------------------------------------------------')

                print(tabulate(table, tablefmt='fancy_grid'))

                print(' ---------------------------------------------------')
                #'--------------------------------------------------------------------------------------------------'
                
                proj_backup = pd.read_excel('../TCE-Settings/Project Data.xlsx')
                if sum(proj_backup['TCE Project #'] == inp) == 0:
                    proj_backup.loc[len(proj_backup.index)] = [inp, proj_logs[0].name, totalTime, employee_cost, expenses_expensify, proj_logs[0].lead.displayName]
                    proj_backup.sort_values(by='TCE Project #', inplace=True)
                    proj_backup.to_excel('../TCE-Settings/Project Data.xlsx', index=False)
                    print(' -- Saved to : Project Data.xlsx')
                else:
                    print(' -- Project Already exists in : Project Data.xlsx')
                
                #'--------------------------------------------------------------------------------------------------'
                inp = input(' - To view expenses in detail enter 1\n - Random key to continue\n - :- ')
                if inp == '1':
                    if expenses_expensify:
                        df_expenses = df_expenses[['Merchant', 'Type', 'Description', 'Date', 'JIRA_ID','Amount', 'M_Amount', 'F_Amount']]
                        print()
                        print(' ---------------------------------------------------')
                        print('      Expensify Details')
                        print(' ---------------------------------------------------')
                        print(tabulate(df_expenses, headers='keys',tablefmt='fancy_grid'))
                    else: print(' --- No expenses found')
                    if type(empwiseTime) != int:
                        print()
                        print(' ---------------------------------------------------')
                        print('      JIRA Work Logs')
                        print(' ---------------------------------------------------')


                        #empwiseTime = [value for value in empwiseTime.values()]
                        #empwiseTime = sorted(empwiseTime, key=lambda x:x[0], reverse=True)
                        #empwiseTime.append([totalTime,'',employee_cost,''])
                        print(tabulate(ammountDue.sort_values(by='Hours', ascending=False), headers='keys', tablefmt='fancy_grid'))
                    else:
                        print(' --- No Jira Logs found')
            system('pause')




        print(' ---- Exiting ----')




#--------------------------
if __name__ == '__main__':
    display()
            



        
