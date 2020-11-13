import boto3
from botocore.exceptions import ClientError


from settings import *


class Arch:

    def __init__(self):
        self.instances = []
        self.ec2 = boto3.client('ec2', region_name="us-east-1")
        self.lb = boto3.client('elbv2', region_name="us-east-1")
        self.subnets = []
        self.sec_group_id = ""




    #Checa se o objeto recebido é meu ou da Manu
    def isMine(self, object):
        for tag in object["Tags"]:
            if tag["Key"] == "Creator" and tag["Value"] == OWNER:
                return True
        return False
    
    def getInstances(self):
        response = self.ec2.describe_instances()
        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:
                if (instance["State"]["Name"]) != "terminated" and self.isMine(instance):
                        self.instances.append(instance["InstanceId"])

    
    # Mata todas as minhas instâncias
    def terminateAll(self):
        print("Terminating existing instances")
        response = self.ec2.terminate_instances(InstanceIds=self.instances)
    
    
    #Deleta um securituGroup pelo seu nome
    def terminateSecurityGroup(self, name):
        print("Terminating existing security group")
        response = self.ec2.delete_security_group(GroupName=name)
        

    #Cria um SecurityGroup pelo seu nome
    def createSecGroup(self, name):
        print("Creating security group ", name)
        try:
            response = self.ec2.create_security_group(
                Description='SecurityGroup created by Leo',
                GroupName= name,
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
            self.terminateSecurityGroup(name)
            return self.createSecGroup(name)

    #Cria n instâncias, recebe a imagem, n de instâncias, security group e nome
    def createInstance(self, image, count, security_group, name):
        print("Creating {0} instance".format(name))
        ids = []
        response = self.ec2.run_instances(
            ImageId = image,
            MinCount = 1,
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
                            'Key': 'Creator',
                            'Value': OWNER
                        }
                    ]
                }]
        )
        for instance in response["Instances"]:
            ids.append(instance["InstanceId"])
        print("Successfully created {0} instances".format(count))
        return ids
    
    def createImage(self, instanceId, name):
        try:
            print("Creating {0} image".format(name))
            response = self.ec2.create_image( InstanceId=instanceId, Name= name)
            print("Successfully created {0} image ".format(name))
            return response['ImageId'] #['Images'][0]['ImageId']
        except ClientError:
            imageId = self.getImage(name)
            self.deleteImage(imageId)
            return self.createImage(instanceId, name)


    def deleteImage(self,imageId ):
        print("Terminating existing image")

        self.ec2.deregister_image(ImageId=imageId)


    def getSubnets(self):
        response = self.ec2.describe_subnets()
        for subnet in response['Subnets']:
            self.subnets.append(subnet["SubnetId"])


    def updateSecurityPort(self, groupName, port):

        print("Setting up security group rules")

        response = self.ec2.authorize_security_group_ingress(
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
    def getImage(self, name):
        response = self.ec2.describe_images(
        Filters=[
            {
                'Name': 'name',
                'Values': [name]
            },
            ]
            )
        return response['Images'][0]['ImageId']

    def getVPCid(self):
        response = self.ec2.describe_vpcs()
        return response['Vpcs'][0]['VpcId']
    

    def deleteExistingTGs(self, name):
        response = self.lb.describe_target_groups()
        for targetGroup in response['TargetGroups']:
            if targetGroup["TargetGroupName"] == name:
                self.deleteTargetGroup(targetGroup["TargetGroupArn"])

    def deleteTargetGroup(self, arn):
        response = self.lb.delete_target_group(TargetGroupArn=arn)





    def createTargetGroup(self, name, port, vpcId):
        try:
            response = self.lb.create_target_group(
                Name = name,
                Port = port,
                VpcId = vpcId,
                TargetType = "instance",
                Protocol = PROTOCOL,
                Tags=[
                {
                    'Key': 'Creator',
                    'Value': OWNER
                },
                ]
            )
            return response['TargetGroups'][0]["TargetGroupArn"]
        except:
            self.deleteExistingTGs(name)
            self.createTargetGroup(name, port, vpcId)


    def registerTarget(self, groupId, targetId):

        response = self.lb.register_targets(
            TargetGroupArn=groupId,
            Targets=[
                {
                    'Id': targetId,
                    },
                ]
            )


        

    def deleteExistingLBs(self, name):
        response = self.lb.describe_load_balancers()
        for loadBalancer in response['LoadBalancers']:
            if loadBalancer["LoadBalancerName"] == name:
                self.deleteLoadBalancer(loadBalancer["LoadBalancerArn"])



    def createLoadBalancer(self, name, subnets):

        try:
            response = self.lb.create_load_balancer(
                Name=name,
                Subnets = subnets,
                Tags=[
            {
                'Key': 'Creator',
                'Value': OWNER
            },]
                )
            return response['LoadBalancers'][0]['LoadBalancerArn']

        except:
            print("Apagando Target Group existente")
            self.deleteExistingLBs(name)
            self.createLoadBalancer(name, subnets)
    

    def deleteLoadBalancer(self, arn):
        response = self.lb.delete_load_balancer(LoadBalancerArn=arn)





    def run(self):
        
        self.getSubnets()
        self.VPC = self.getVPCid()

        self.getInstances()
        if self.instances != [] : 
            self.terminateAll()
            waiter = self.ec2.get_waiter('instance_terminated')
            waiter.wait(InstanceIds= self.instances)
        self.instances = []
        
        security_group = self.createSecGroup("teste-leo") 
        DEFAULT_IMG = self.getImage(DEFAULT_IMG_NAME )
        instance = self.createInstance(DEFAULT_IMG, 1, [security_group], "loe")
        waiter2 = self.ec2.get_waiter('instance_running')
        waiter2.wait(InstanceIds= instance)
        #self.updateSecurityPort("teste-leo", 8080)
        #ami_id = self.createImage(instance[0], "ami-uwu")
#
        #waiter = self.ec2.get_waiter('image_available')
        #waiter.wait(ImageIds = [ami_id])
        #instance = self.createInstance(ami_id, 1, [security_group], "loe-ami")
#
        #self.lbID = self.createLoadBalancer("lb-loe", self.subnets)
        


        #FALTA  A PORTAAAAAAAAAAAAAAAAAAA AQUI DEU ERRO
        targetARN = self.createTargetGroup("leowo", 84, self.VPC)

        self.registerTarget(targetARN, instance[0])
    



        
        

        print("END")


app = Arch()
app.run()
