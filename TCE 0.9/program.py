from tce_expensify import get_expensify
from tabulate import tabulate
import json

class TCEJIRA(object):
    def __init__(self, jiraserver, auth):
        from jira import JIRA
        self.jira = JIRA(server=jiraserver, basic_auth=auth)

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
    def queryProjIssues(self, projectkey=None):
        if projectkey == None:
            print('\n\n Error: Please Enter a Project Key.')
            return None
        project = self.queryProj(projectkey)
        if project == None:
            return [None, None]
        else:
            try:
                issues = self.jira.search_issues(f'project={projectkey}',
                   fields=('timespent', 'summary', 'reporter', 'assignee', 'progress', 'status'),
                   json_result=True)
                proj_issues = [project, issues]
            except:
                print("\n\n Error: Check Internet Connection or Try Again.")
                issues = None
                proj_issues = [project, issues]
        return proj_issues

#-----------------Usefull Functions-------------------------------------------------------------------

def fileSelector():
    import pandas as pd
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
def empWiseTimeCalc(issues = None):
    '''Add Docstring'''
    if not(issues) or issues['total'] == 0:
        return 0

    unique_reporters = set()
    unique_names = dict()
    for issue in issues['issues']:
        unique_reporters.add(issue['fields']['reporter']['accountId'])
        unique_names[issue['fields']['reporter']['accountId']] = issue['fields']['reporter']['displayName']
        
    emp_timelog = dict(zip(unique_reporters, [0] * len(unique_reporters)))
    
    for issue in issues['issues']:
        emp_timelog[issue['fields']['reporter']['accountId']] += issue['fields']['progress']['progress']
    
    #convert time from seconds to hours
    emp_timelog.update((x, y/3600) for x, y in emp_timelog.items())
    #add emp name to dictionary 'accountId':[time, emp name]
    for key in emp_timelog.keys():
        emp_timelog[key] = [emp_timelog[key], unique_names[key]]

    return emp_timelog

#       -------------------------------------
def profitCalculator(empwiseTime, proposalamount = None, hourlyRates={"others": [35, '']}):
    if type(empwiseTime) == dict:
        for key in empwiseTime.keys():
            if key in hourlyRates.keys():
                empwiseTime[key].extend([empwiseTime[key][0] * hourlyRates[key][0], hourlyRates[key][0]])
            else:
                empwiseTime[key].extend([empwiseTime[key][0] * hourlyRates["others"][0], hourlyRates["others"][0]])
        
        total_expense = sum([val[2] for val in empwiseTime.values()])
        return (proposalamount - total_expense), total_expense, empwiseTime #Profit, employee_cost
    else:
        return proposalamount, 0, empwiseTime




# --Display--------------------------------------------------------------------------------------------------
def display():
        from os import system
        inp = ''
        
        print(' Connecting with JIRA ----- Please Wait')
        jira = TCEJIRA(jiraserver='https://towerce.atlassian.net/', auth=('email@gmail.com', 'api-hash'))
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
            proj_issues = jira.queryProjIssues(inp)
            if proj_issues[0] != None:        
                print(' -- Fetching Data from Expensify')
                df_expenses = get_expensify(inp)
                system('cls')
                print()
                print(' ---- Tower Consulting Engineers ----')
                print('\n Project ID: ', inp)
                print(' Project:    ', proj_issues[0].name)
                print(' Lead:       ', proj_issues[0].lead.displayName)
                print(' ---------------------------------------------------')
                #Getting Proposal Amount from the file, calculating total project time and finding profit.
                try:
                    proposalamount = int(jobs[jobs['IN JIRA'] == inp]['TOTAL PROPOSAL AMOUNT '])
                except:
                    print(' "Proposal Amount for this project is not listed in the excel sheet."')
                    print(' ---------------------------------------------------')
                    proposalamount = 0
                empwiseTime = empWiseTimeCalc(proj_issues[1])
                profit, employee_cost, empwiseTime = profitCalculator(empwiseTime, 
                                                                      proposalamount,
                                                                      tce_settings['hourlyRate'])
                expenses_expensify = df_expenses['F_Amount'].sum()
                profit -= expenses_expensify
                if type(empwiseTime) == dict:
                    totalTime = sum([val[0] for val in empwiseTime.values()])
                else: totalTime = 0

                table = [['Total Time Logged (JIRA)', f'{totalTime:.2f} Hrs'],
                         ['Total Jobs', proj_issues[1]["total"]],
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
                    if type(empwiseTime) == dict:
                        print()
                        print(' ---------------------------------------------------')
                        print('      JIRA Work Logs')
                        print(' ---------------------------------------------------')
                        empwiseTime = [value for value in empwiseTime.values()]
                        empwiseTime = sorted(empwiseTime, key=lambda x:x[0], reverse=True)
                        empwiseTime.append([totalTime,'',employee_cost,''])
                        print(tabulate(empwiseTime, headers=['Hours Logged','Reporters Name','Amount Due','Hourly Rate'], tablefmt='fancy_grid'))
                    else:
                        print(' --- No Jira Logs found')
            system('pause')




        print(' ---- Exiting ----')




#--------------------------
if __name__ == '__main__':
    display()
            



        