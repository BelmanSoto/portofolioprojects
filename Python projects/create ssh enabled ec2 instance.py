#Import boto3 library, then define ec2 client
import logging
import boto3
import time
import pprint
from botocore.exceptions import ClientError
import os

ec2_client = boto3.client('ec2', region_name='us-east-1')
ec2 = boto3.resource('ec2')

#Prompt user for a ec2 name
ec2Name = input('Enter a unique name for your ec2: ')
namecheck = str(ec2_client.describe_instances())

while True :
    if ec2Name in namecheck :
        ec2Name = input ('That name already exists, try again ')
        continue
    else :
        break

#Gets the default vpc id for use by the security group
response = ec2_client.describe_vpcs()
vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')


#function to create a security group
def create_securuity_group () :
        #we set the name we want to use to a variable. will be used by 'GroupName'
        sg_name = 'new_python_project'
        #creates a global variable for the security group id so that it can be passed to the instance
        global security_group_id
        try:
            #builds the security group and sets the ports for ssh and sets it to the response variable so that we can filter for other things
            response = ec2_client.create_security_group(GroupName=sg_name,
                                                Description='This sg was created using python',
                                                VpcId=vpc_id)
            #Greps the value of the security group id. Works because the security group was created and saved as response
            security_group_id = response['GroupId']
            # print('Security Group Created %s in vpc %s.' % (security_group_id, vpc_id))

            #sets the inbound traffic protocols
            sg_config = ec2_client.authorize_security_group_ingress(
                GroupId=security_group_id,
                IpPermissions=[
                    # {'IpProtocol': 'tcp',
                    # 'FromPort': 80,
                    # 'ToPort': 80,
                    # 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}, accepts all ip's. public access.
                    {'IpProtocol': 'tcp',
                    'FromPort': 22, #ssh port
                    'ToPort': 22,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
                ]) 
        #if the name already exists for the sg, it gets the security group id and assigns it to the sg_id value to be used
        except ClientError as e:
            if str(e).__contains__('already exists') :
                response = ec2_client.describe_security_groups(GroupNames=[sg_name])
                security_group_id = response["SecurityGroups"][0]['GroupId']
            else: print(e)


def create_keypair () :
    global kpname
    while True:
        try:  
            kpname = input('Please enter a unique key name: ')
            response = ec2_client.create_key_pair(
                KeyName= kpname
            )
            accesskey = response['KeyMaterial']
            with open(f'{kpname}.pem', 'w' ) as f:
                f.write(accesskey) 
            print('Successfully created the keypair and saved it to a file in your directory!')
            time.sleep(3)
            break
            # os.system('cls')
        except: 
            print('That name is already in use.')
            time.sleep(1)
            continue

def create_ec2_instance() :
    try: 
        print('Creating ec2 instance')
        ec2_client.run_instances(
            ImageId = 'ami-09d3b3274b6c5d4aa',
            MinCount = 1,
            MaxCount = 1,
            InstanceType = 't2.micro',
            KeyName = kpname,
            SecurityGroupIds=[security_group_id],
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': ec2Name }       ] } ] #using the Tags with this key we name the instance what the user chose at the beginning
        )
        time.sleep(1)
        print(f'Your {ec2Name} instance has been created.')
        time.sleep(2)
        # os.system('cls')
    except Exception as e:
        print(e)

def check_status( ):
    print('Checking your instance status')
    global inId
    filters = [{'Name':'tag:Name', 'Values':[ec2Name]}]
    time.sleep(1.5)
    state = True
    while state == True :
        #This loop iterates through the dictionary value that describe_instances returns so that we can get the instance Id for the instance that the user created for use in check_health
        #and checks assigns to state of the instance to a variable for a conditional statement
        for each in ec2_client.describe_instances(Filters=filters)['Reservations']:
            for each_in in each['Instances']:
                #print(each_in['InstanceId'], each_in['State']['Name'])
                response = str(each_in['State']['Name'])
                inId = [str(each_in['InstanceId'])]
        if response == 'running':
            print(f'Your {ec2Name} instance is running. Waiting on health checks')
            state = False
            time.sleep(2)
        elif response == 'pending':
            print(f'Your, {ec2Name}, instance is still booting up. Checking again in 10 seconds')
            time.sleep(10)
            continue
    
    #status= ec2_client.describe_instance_status(InstanceIds = inId, IncludeAllInstances = True)
    #print(status)

def check_health() :
    status = True
    count = 0
    while status == True :
        #without putting the dictionary output into an array, you can not iterate down to the 'Status' key
        #This checks if the instance is accepting traffic yet
        for each in [ec2_client.describe_instance_status(InstanceIds=inId, IncludeAllInstances = True)['InstanceStatuses'][0]['InstanceStatus']]:
            for x in each['Details']:
                stat = str(x['Status'])
        if stat == 'passed' :
            print(f'Your "{ec2Name}", instance has passed its health checks and is now ready to use. The Key Pair is {kpname}')
            status = False
        elif stat == 'initializing' :
            if count == 0:
                print('Health checks are initializing')
                count = count + 1
            elif 0< count <2 :
                print('This will take a few minutes')
                count = count + 1
            elif count >= 2 :
                print('Pinging instance')
            time.sleep(10)
            continue
        elif stat == 'failed' :
            print('Heatlh checks failed.')
            status = False 

def ask_key() :
    try:
        userkey = input('Do you want to use an existing key for this instance? (Yes/No) ')
    except ClientError as e :
        print(e)
        quit()
    state = True
    global kpname
    if userkey == 'Yes' :
        keyNames = []
        response = ec2_client.describe_key_pairs()
        for item in response['KeyPairs']:
            keyNames.append(item['KeyName'])
        print('Your existing keys are as follows:')
        for each in keyNames :
            print(each)
        try:
            while state == True :
                kpname = input('Enter a keypair name from above: ')
                if kpname not in (keyNames) :
                    print('Double check your input. Match the key pair name precisely')
                    time.sleep(3)
                    continue
                else:
                    state = False
                    break
        except ClientError as e:
            print(e)
    elif userkey == 'No':
        create_keypair()
        state = False
    else:
        print('Only Yes or No are acceptable answers. Try again.')
        quit()


ask_key()
create_securuity_group()
create_ec2_instance()
check_status()
check_health()

'''response = [ec2_client.describe_instance_status(InstanceIds=['i-0c5b221f90fddb6b0'], IncludeAllInstances = True)['InstanceStatuses'][0]['InstanceStatus']]
print(response)
#print(response[0]['Details'][0]['Status'])


for each in [ec2_client.describe_instance_status(InstanceIds=['i-0c5b221f90fddb6b0'], IncludeAllInstances = True)['InstanceStatuses'][0]['InstanceStatus']]:
    for x in each['Details']:
        print(x['Status'])'''
