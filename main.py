import boto3
from botocore.exceptions import ClientError
import time
from settings import *


class Arch:

    def __init__(self):
        self.instances = []
        self.ec2_east1 = boto3.client('ec2', region_name="us-east-1")
        self.ec2_east2 = boto3.client('ec2', region_name="us-east-2")

        self.lb = boto3.client('elb', region_name="us-east-1")
        self.subnets = []
        self.auto = boto3.client('autoscaling', region_name="us-east-1")

    def getDjangoScript(self, IP):
        return """#!/bin/bash
                cd /home/ubuntu
                sudo apt update -y
                git clone https://github.com/raulikeda/tasks
                sed -i "s/node1/{0}/"  /home/ubuntu/tasks/portfolio/settings.py
                sed -i "s/cloud/cloud9/" /home/ubuntu/tasks/install.sh
                cd tasks
                ./install.sh
                sudo reboot
        """.format(IP)

    def isMine(self, object):
        # Checa se o objeto recebido é meu ou da Manu
        for tag in object["Tags"]:
            if tag["Key"] == "Creator" and tag["Value"] == OWNER:
                return True
        return False

    def getSubnets(self, ec2):
        response = ec2.describe_subnets()
        for subnet in response['Subnets']:
            self.subnets.append(subnet["SubnetId"])

    def getInstances(self, ec2):
        response = ec2.describe_instances()
        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:
                if (instance["State"]["Name"]) != "terminated" and self.isMine(instance):
                    self.instances.append(instance["InstanceId"])

    def terminateAll(self, ec2):
        # Mata todas as minhas instâncias
        print("Terminating existing instances")
        response = ec2.terminate_instances(InstanceIds=self.instances)

    def createSecGroup(self, ec2, name):
        # Cria um SecurityGroup
        print("Creating security group ", name)
        try:
            response = ec2.create_security_group(
                Description='SecurityGroup created by Leo',
                GroupName=name,
                TagSpecifications=[
                    {
                        'ResourceType': 'security-group',
                        'Tags': [
                            {
                                'Key': 'Creator',
                                'Value': OWNER
                            },
                        ]
                    },
                ]
            )
            print("Successfully created Security Group ", name)
            return response["GroupId"]
        except ClientError:
            self.terminateSecurityGroup(ec2, name)
            return self.createSecGroup(ec2, name)

    def terminateSecurityGroup(self, ec2, name):
        # Deleta um securituGroup pelo seu nome
        try:
            print("Terminating existing security group")
            response = ec2.delete_security_group(GroupName=name)
        except:
            self.deleteExistingAutos(AUTO_SCALING_NAME)
            self.deleteExistingLCs(AUTO_SCALING_NAME)
            self.terminateSecurityGroup(ec2, name)

    def createInstance(self, ec2, image, count, security_group, name, script):
        # Cria n instâncias, recebe a imagem, n de instâncias, security group e nome
        print("Creating {0} instance".format(name))
        ids = []
        ip = None
        response = ec2.run_instances(
            ImageId=image,
            InstanceType=INSTANCE_TYPE,
            KeyName=KEY_NAME,
            MinCount=1,
            MaxCount=count,
            SecurityGroupIds=security_group,
            UserData = script,            
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': name
                        },
                        {
                            'Key': 'Creator',
                            'Value': OWNER
                        },
                    ]
                }]
        )
        for instance in response["Instances"]:
            ids.append(instance["InstanceId"])
        waiter2 = ec2.get_waiter('instance_status_ok')
        waiter2.wait(InstanceIds=ids)
        response = ec2.describe_instances()
        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:
                if (instance["State"]["Name"]) != "terminated" and instance["InstanceId"]== ids[0]:
                    ip = instance["PublicIpAddress"]
                            
        
        print("Successfully created {0} instances".format(count))
        return ids, ip

    def createImage(self, ec2, instanceId, name):
        try:
            print("Creating {0} image".format(name))
            response = ec2.create_image(InstanceId=instanceId, Name=name)
            print("Successfully created {0} image ".format(name))
            return response['ImageId']  # ['Images'][0]['ImageId']
        except ClientError:
            imageId = self.getImage(name)
            self.deleteImage(imageId)
            return self.createImage(ec2, instanceId, name)

    def deleteImage(self, ec2, imageId):
        print("Terminating existing image")
        ec2.deregister_image(ImageId=imageId)

    def updateSecurityPort(self, ec2, groupName, port):

        print("Setting up security group rules")

        response = ec2.authorize_security_group_ingress(
            GroupName=groupName,
            IpPermissions=[
                {
                    'FromPort': port,
                    'IpProtocol': 'TCP',
                    'IpRanges': [
                        {
                            'CidrIp': '0.0.0.0/0',
                            'Description': 'string'
                        },
                    ],
                    'ToPort': port
                }
            ]
        )

    def getImage(self, ec2, name):
        response = ec2.describe_images(
            Filters=[
                {
                    'Name': 'name',
                    'Values': [name]
                },
            ]
        )
        return response['Images'][0]['ImageId']

    def deleteLoadBalancer(self, name):
        response = self.lb.delete_load_balancer(LoadBalancerName=name)

    def createLoadBalancer(self, name, subnets, lb_port, inst_port, security_group):

        try:
            response = self.lb.create_load_balancer(
                LoadBalancerName=name,
                Subnets=subnets,
                Listeners=[
                    {
                        'Protocol': PROTOCOL,
                        'LoadBalancerPort': lb_port,
                        'InstancePort': inst_port,
                    },
                ],
                    SecurityGroups=[security_group],
                Tags=[
                    {
                        'Key': 'Creator',
                        'Value': OWNER
                    }, ]
            )
            return response['DNSName']
        except:
            self.deleteLoadBalancer(name)
            self.createLoadBalancer(name, subnets, lb_port, inst_port)

    def createAutoScaling(self, name, LoadBalancerName, instanceId, min, max):
        try:
            response = self.auto.create_auto_scaling_group(
                AutoScalingGroupName=name,
                InstanceId=instanceId,
                MinSize=min,
                MaxSize=max,
                LoadBalancerNames=[LoadBalancerName],
                Tags=[
                    {
                        'Key': 'Creator',
                        'Value': OWNER
                    },
                ]
            )
        except:
            self.deleteExistingAutos(name)
            self.deleteExistingLCs(name)
            self.createAutoScaling(
                name, LoadBalancerName, instanceId, min, max)

    def deleteExistingLCs(self, name):
        response = self.auto.describe_launch_configurations(
            LaunchConfigurationNames=[name])
        for launchConfig in response['LaunchConfigurations']:
            if launchConfig['LaunchConfigurationName'] == name:
                self.deleteLaunchConfiguration(name)

    def deleteLaunchConfiguration(self, name):
        response = self.auto.delete_launch_configuration(
            LaunchConfigurationName=name)

    def deleteExistingAutos(self, name):
        response = self.auto.describe_auto_scaling_groups(
            AutoScalingGroupNames=[name])
        for auto in response['AutoScalingGroups']:
            if auto['AutoScalingGroupName'] == name:
                self.deleteAutoScaling(name)

    def deleteAutoScaling(self, name):
        response = self.auto.delete_auto_scaling_group(
            AutoScalingGroupName=name,
            ForceDelete=True
        )

        

    def run(self):

        self.getSubnets(self.ec2_east1)
#
        self.deleteExistingAutos(AUTO_SCALING_NAME)
        self.deleteExistingLCs(AUTO_SCALING_NAME)
        self.deleteLoadBalancer(LOAD_BALANCER_NAME)
        
        
        #Apagando todas instancias East-1
        self.getInstances(self.ec2_east1)
        if self.instances != []:
            self.terminateAll(self.ec2_east1)
            waiter = self.ec2_east1.get_waiter('instance_terminated')
            waiter.wait(InstanceIds=self.instances)
        self.instances = []

        #Apagando todas instancias East-2
        self.getInstances(self.ec2_east2)
        if self.instances != []:
            self.terminateAll(self.ec2_east2)
            waiter = self.ec2_east2.get_waiter('instance_terminated')
            waiter.wait(InstanceIds=self.instances)
        self.instances = []

        security_group_postgres = self.createSecGroup(self.ec2_east2, SECURITY_GROUP_NAME)
        self.updateSecurityPort(self.ec2_east2, SECURITY_GROUP_NAME, 22)
        self.updateSecurityPort(self.ec2_east2, SECURITY_GROUP_NAME, 8080)
        self.updateSecurityPort(self.ec2_east2, SECURITY_GROUP_NAME, 5432)


        DEFAULT_IMG = self.getImage(self.ec2_east2 ,DEFAULT_IMG_NAME)
        instance, postgres_ip = self.createInstance(self.ec2_east2, DEFAULT_IMG, 1, [security_group_postgres], POSTGRES_NAME, POSTGRES_SCRIPT)
        
                
        security_group_django = self.createSecGroup(self.ec2_east1, SECURITY_GROUP_NAME)
        self.updateSecurityPort(self.ec2_east1, SECURITY_GROUP_NAME, 22)
        self.updateSecurityPort(self.ec2_east1, SECURITY_GROUP_NAME, 8080)
        self.updateSecurityPort(self.ec2_east1, SECURITY_GROUP_NAME, 5432)


    
        DEFAULT_IMG = self.getImage(self.ec2_east1 ,DEFAULT_IMG_NAME)
        instances, djangoIP = self.createInstance(self.ec2_east1, DEFAULT_IMG, 1, [security_group_django], "loe", self.getDjangoScript(postgres_ip))

        
        DNSlb = self.createLoadBalancer(LOAD_BALANCER_NAME, self.subnets, 8080, 8080, security_group_django)
        self.createAutoScaling( AUTO_SCALING_NAME, LOAD_BALANCER_NAME, instances[0], 1, 3)

        print("Acesse por: {0}".format(DNSlb))

        print(" THE END.")


app = Arch()
app.run()
