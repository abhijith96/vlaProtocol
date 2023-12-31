from math import pi
import subprocess
import re
import time
import signal
import os
import csv

MININET_FILE_PATH = "/home/VlaTests/hostMacs.csv"
RTT_FILE_PATH = "/home/VlaTests/RTT.csv"


pingReceiverProgram = "/home/VlaTests/VlaPingListener.py"
pingSenderProgram = "/home/VlaTests/VlaPing.py" 


def read_csv_to_dict(file_path):
    data_dict = {}
    with open(file_path, 'rb') as csv_file:
        csv_reader = csv.reader(csv_file)

        # Skip the header row if it exists
        next(csv_reader, None)

        for row in csv_reader:
            key = row[0]
            value = row[1]
            data_dict[key] = value

    return data_dict

def write_dict_to_csv(file_path, data_dict):
    with open(file_path, 'wb') as csv_file:
        # Use csv.writer to write to the CSV file
        csv_writer = csv.writer(csv_file)

        # Write the header row (optional)
        header = ["hostName", "RoundTripTime"]
        csv_writer.writerow(header)

        # Write the data rows
        for key, value in data_dict.items():
            row = []
            row.append(key[0])
            row.append(key[1])
            row.append(value)
            csv_writer.writerow(row)


def get_rest_of_string_after_prefix(input_string, prefix):
    prefix_position = input_string.find(prefix)
    if prefix_position != -1:
        rest_of_string = input_string[prefix_position + len(prefix):]
        return rest_of_string
    else:
        return None

def extractHostNameAndPid(input_string):
    # Split the string into words
    hostName = None
    processId = None
    words = input_string.split()

    # Check if the string has at least 3 words
    if len(words) >= 4:
        # Print the third word
        processId = words[3]

    # Check if the string has at least 1 word
    if len(words) >= 1:
        # Print the last word
        hostName = get_rest_of_string_after_prefix(words[-1], "mininet:")
    
    return (processId, hostName)

def getNetworkNamespaces():
    try:
        # Run the shell command and capture the output
        result = subprocess.check_output("lsns --type=net", shell=True)

        # Split the output into lines and return as a list
        return result.strip().split('\n')
    except subprocess.CalledProcessError as e:
        print("Error: %s ".format(e))
        return []
    

def run_python_file_in_namespace(namespace_name, python_file_path, arg=None):
    try:
        # Use nsenter to enter the network namespace and run the Python file
        nsenter_command = None
        if(arg):
            nsenter_command = ["nsenter", "--net", "--mount", "--ipc", "--pid", "--uts", "--target", namespace_name, "python", python_file_path, arg]
        else:    
            nsenter_command = ["nsenter", "--net", "--mount", "--ipc", "--pid", "--uts", "--target", namespace_name, "python", python_file_path]
        process = subprocess.Popen(nsenter_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return process

    except subprocess.CalledProcessError as e:
            print("Error: " % e)
            return None


def getMininetHostNamesAndProcessIds():
    output = getNetworkNamespaces()
    output_hosts = []
    for line in output:
        (procoess_id, hostName) = extractHostNameAndPid(line)
        if(procoess_id and hostName):
            output_hosts.append((hostName, procoess_id))
    return output_hosts



def runPingForHostPair(senderHostName, senderHostProcessId, receiverHostName, receiverHostMac, receiverHostProcessId):
    global pingSenderProgram
    global pingReceiverProgram
    pingPythonCommand = pingSenderProgram
    pingListenerPythonCommand = pingReceiverProgram
       # Run the first Python file in the first namespace
    ping_listener_process = run_python_file_in_namespace(receiverHostProcessId, pingListenerPythonCommand)

    # Wait for a moment to ensure the first file is running
    time.sleep(1)

    # Run the second Python file in the second namespace
    ping_sender_process = run_python_file_in_namespace(senderHostProcessId, pingPythonCommand, arg=receiverHostMac)

    # Wait for the second file to finish and capture its output
    output, errors = ping_sender_process.communicate()

    # Terminate the first file when the second file ends
    poll = ping_listener_process.poll()
    if(poll is None):
        ping_listener_process.terminate()

    # Optionally wait for the first file to terminate gracefully
    #ping_listener_process.wait()

    outputString = output.decode('utf-8')


    print("output is ",outputString)

    outputLines = outputString.split("\n")

    for line in outputLines:
        if line.startswith("RoundTripTimeis"):
            words = line.split()
            if(len(words) >= 2):
                round_trip_time = words[1]
                return (True,round_trip_time)
    return (False, None)
    



def main():
    output_hosts = getMininetHostNamesAndProcessIds()
    hostMacMap = read_csv_to_dict(MININET_FILE_PATH)
    hostCount = len(output_hosts)
    rttDict = {}
    for i in range(0, hostCount):
        for j in range(i+ 1, hostCount):
            senderHostName = output_hosts[i][0]
            receiverHostName = output_hosts[j][0]
            senderPid = output_hosts[i][1]
            receiverPid = output_hosts[j][1]

            receiverMac= hostMacMap[receiverHostName]

            rttFound, rtt = runPingForHostPair(senderHostName, senderPid, receiverHostName, receiverMac, receiverPid)
            if(rttFound):
                print("rtt " + rtt)
                rttDict[(senderHostName, receiverHostName)] = rtt

    write_dict_to_csv(RTT_FILE_PATH, rttDict)

    





   


   

    # Run the first Python file in the first namespace
    # process_1 = run_python_file_in_namespace(namespace_name_1, python_file_path_1)

    # # Wait for a moment to ensure the first file is running
    # time.sleep(1)

    # # Run the second Python file in the second namespace
    # process_2 = run_python_file_in_namespace(namespace_name_2, python_file_path_2)

    # # Wait for the second file to finish and capture its output
    # output, errors = process_2.communicate()

    # # Terminate the first file when the second file ends
    # process_1.terminate()

    # # Optionally wait for the first file to terminate gracefully
    # process_1.wait()

    # outputLines = output.decode('utf-8').split("\n")

    # for line in outputLines:
    #     if line.startswith("RoundTripTimeis"):
    #         words = line.split()
    #         if(len(words) >= 2):
    #             round_trip_time = words[1]

    # print("Output of the second file:")
    # print(output.decode('utf-8'))
    # print("Errors of the second file:")
    # print(errors.decode('utf-8'))
    # print("Both files completed.")

if __name__ == "__main__":
    main()

    