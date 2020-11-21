#!/usr/bin/env python

import sys
import requests
import dateutil.parser
from datetime import datetime




def getTasks(dns):
    try :
        response = requests.get(f'http://{dns}:8080/tasks')
        return response.json()
    except:
        return "No response"

def insertTask(dns,title, pub_date, description_list):
    try:
    
        description = ' '.join(description_list)

        datetime_object = datetime.strptime(pub_date, '%d/%m/%Y').isoformat()

        jsonObj = {
                "title" : title,
                "pub_date" : datetime_object,
                "description" : description
            }
        response = requests.post(
            url= f'http://{dns}:8080/tasks/insert',
            data= jsonObj)
        if response.status_code == 201:
            return "Task created successfully"
        return "Error, check your arguments"
    except:
        return "No response"


def run(arg):

    #Lê o DNS no arquivo criado pelo main.py
    with open('dns.txt','r') as file:
        dns = file.readline().strip("\n")
        file.close()

    #Checa o número de argumentos 
    arguments = len(arg) - 1
    
    #DO nothing
    if arguments ==0:
        print("Argument is none.")
    elif arg[1] == "list":
        response = getTasks(dns)
        if response != "No response":
            for obj in response:
                data = dateutil.parser.parse(obj['pub_date'])
                print(obj['title'])
                print("{0}".format(data.strftime('%m/%d/%Y')))
                print(obj['description'],"\n")
        else:
            print(response)



    elif arguments >=4 and arg[1].lower() == "post":

        response = insertTask(dns, arg[2],arg[3] ,arg[4:])
        print(response)
    else:
        print("Command is not valid.")
    


if __name__ == "__main__":
    run(sys.argv)