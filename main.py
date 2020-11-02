import boto3


from settings import *


class Arch:

    def __init__(self):
        self.instances = []
        self.ec2 = boto3.client('ec2')

    def getInstances(self):
        response = self.ec2.describe_instances()
        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:
                if (instance["State"]["Name"]) != "terminated":
                    self.instances.append(instance["InstanceId"])

    # Mata todas as instâncias

    def terminateAll(self):
        response = self.ec2.terminate_instances(InstanceIds=self.instances)
        self.instances = []

    def createInstance(self, image, count, security_group, name):
        ids = []
        response = self.ec2.run_instances(
            ImageId=image,
            InstanceType=INSTANCE_TYPE,
            MinCount=1,
            MaxCount=count,
            SecurityGroupIds=security_group,
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': name
                        },
                        {
                            'Key': 'Owner',
                            'Value': OWNER
                        }
                    ]
                }]
        )
        for instance in response["Instances"]:
            ids.append(instance["InstanceId"])
        return ids


    def initialSetup(self):
        #Testando a createInstance
        response = self.createInstance(DEFAULT_IMG, 3, [SECURITY_GROUP], "dddddd")

    def run(self):
        self.getInstances()
        if self.instances != [] : self.terminateAll() 
        self.initialSetup()


app = Arch()
app.run()
