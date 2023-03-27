from socket import *
import os
import sys
import struct
import time
import select
import binascii
import pandas as pd
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)

ICMP_ECHO_REQUEST = 8


def checksum(string):
    csum = 0
    countTo = (len(string) // 2) * 2
    count = 0

    while count < countTo:
        thisVal = (string[count + 1]) * 256 + (string[count])
        csum += thisVal
        csum &= 0xffffffff
        count += 2

    if countTo < len(string):
        csum += (string[len(string) - 1])
        csum &= 0xffffffff

    csum = (csum >> 16) + (csum & 0xffff)
    csum = csum + (csum >> 16)
    answer = ~csum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer


def receiveOnePing(mySocket, ID, timeout, destAddr):
    timeLeft = timeout

    while 1:
        startedSelect = time.time()  # Current time in sec.
        whatReady = select.select([mySocket], [], [], timeLeft)
        howLongInSelect = (time.time() - startedSelect)
        if whatReady[0] == []:  # Timeout
            return "Request timed out."

        timeReceived = time.time()  # Current time recorded if socket ready.
        recPacket, addr = mySocket.recvfrom(1024)

        # Fill in start

        # Fetch the ICMP header from the IP packet

        # In IP datagram, IP is first 20 bytes, ICMP is 8 bytes after.
        ICMP_Header = recPacket[20:28]
        # Unpacking the header, format string "bbHHh" specifies how unpacked values are assigned to variables.
        # struct.unpack- unpacks binary string to tuple values.
        # Takes first argument a format string that specifies data type/byte order and 2nd argument is a packed binary string to be unpacked.
        Req_Type, Code, CheckSum, ID_Num, Seq_Num = struct.unpack("bbHHh", ICMP_Header)

        if Req_Type != 8 and ID_Num == ID:
            SizeInDouble = struct.calcsize("d")  # Calculating size of packed double precision floating pt. no.
            Extract_Timestamp = (recPacket[28:28 + SizeInDouble])  # Timestamp value follows ICMP header, starts at 28 up to "d" calculated in Line 61.If d = 8, extracted from [28:36]
            TimestampInPayload = struct.unpack("d", Extract_Timestamp)[0]  # struct.unpack returns tuple, retrieving only first value.
            RTT = timeReceived - TimestampInPayload
            bytes = len(recPacket)
            ttl = str(recPacket[8:8])
            remaining = (RTT*1000, bytes, ttl)
            return(remaining)
        else:
            return ['0', '0.0', '0', '0.0']
        # Fill in end
        timeLeft = timeLeft - howLongInSelect
        if timeLeft <= 0:
            return "Request timed out."


def sendOnePing(mySocket, destAddr, ID):
    # Header is type (8), code (8), checksum (16), id (16), sequence (16)

    myChecksum = 0
    # Make a dummy header with a 0 checksum
    # struct -- Interpret strings as packed binary data

    # Creating dummy header and formatting to byte string using format string "bbHHh", passing arguments to function)
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    # Creating byte string representing data payload containing timestamp in double-prec fp num.
    data = struct.pack("d", time.time())
    # Calculate the checksum on the data and the dummy header (Packet).
    myChecksum = checksum(header + data)

    # Get the right checksum, and put in the header

    if sys.platform == 'darwin':
        # Convert 16-bit integers from host to network  byte order
        myChecksum = htons(myChecksum) & 0xffff
    else:
        myChecksum = htons(myChecksum)

    # Recreating header with correct checksum
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    packet = header + data

    # Sending ICMP pkt to specified Addrs.
    mySocket.sendto(packet, (destAddr, 1))  # AF_INET address must be tuple, not str

    # Both LISTS and TUPLES consist of a number of objects
    # which can be referenced by their position number within the object.


def doOnePing(destAddr, timeout):
    icmp = getprotobyname("icmp")

    # SOCK_RAW is a powerful socket type. For more details:   https://sock-raw.org/papers/sock_raw
    mySocket = socket(AF_INET, SOCK_RAW, icmp)

    myID = os.getpid() & 0xFFFF  # Return the current process i
    sendOnePing(mySocket, destAddr, myID)
    delay = receiveOnePing(mySocket, myID, timeout, destAddr)
    mySocket.close()
    return delay


def ping(host, timeout=1):
    # timeout=1 means: If one second goes by without a reply from the server,
    # the client assumes that either the client's ping or the server's pong is lost
    dest = gethostbyname(host)
    print("\nPinging " + dest + " using Python:")
    print("")

    response = pd.DataFrame(columns=['bytes', 'rtt', 'ttl'])  # This creates an empty dataframe with 3 headers with the column specific names declared

    # Send ping requests to a server separated by approximately one second
    # Add something here to collect the delays of each ping in a list, so you can calculate vars after your ping
    #print(response)
    #delays = []
    for i in range(0, 4):  # Four pings will be sent (loop runs for i=0, 1, 2, 3)
        delay, statistics = doOnePing(dest, timeout)  # what is stored into delay and statistics?
        #print("Reply from: " + dest + " time: " + str(round(delay, 2) ) + " ms")
        #delays.append(delay)
        response = response.append({'bytes': statistics[0], 'rtt': delay, 'ttl': statistics[1]},
                                   ignore_index=True)# store your bytes, rtt, and ttle here in your response pandas dataframe. An example is commented out below for vars
        #print(response)
        #print(delay)
        #print(statistics)

        print("Reply from: " + dest + " bytes: " + str(round(statistics[0], 2)) + " time: " + str(
            round(delay, 7)) + " ms" + " TTL: " + str(round(statistics[0], None)))
        time.sleep(1)  # wait one second

    packet_lost = 0
    packet_recv = 0

    # fill in start. UPDATE THE QUESTION MARKS
    for index, row in response.iterrows(): # Looping through each row in response df
        if statistics[0] == 0:  # access your response df to determine if you received a packet or not
            packet_lost += 1
        else:
            packet_recv += 1
    print("--- google.com ping statistics --- ")

    print( "4 packets transmitted," + str(packet_recv) + " packets received, " + str((packet_lost/4)*100) + "% packet loss")

    # fill in end
    # print(delays)
    # You should have the values of delay for each ping here structured in a pandas dataframe;
    # fill in calculation for packet_min, packet_avg, packet_max, and stdev
    #packet_min = min(delays)
    #packet_avg = sum(delays)/4
    #packet_max = max(delays)
    #stddev = statistics.stdev(delays)
    vars = pd.DataFrame(columns=['min', 'avg', 'max', 'stddev'])
    vars = vars.append({'min': str(round(response['rtt'].min(), 2)), 'avg': str(round(response['rtt'].mean(), 2)),
                       'max': str(round(response['rtt'].max(), 2)), 'stddev': str(round(response['rtt'].std(), 2))}, ignore_index=True)
    #vars = vars.append({'min': str(round(packet_min, 2)), 'avg': str(round(packet_avg, 2)),
                        #'max': str(round(packet_max, 2)), 'stddev': str(round(stddev, 2))},
                       #ignore_index=True)
    print(vars)  # make sure your vars data you are returning resembles acceptance criteria
    return vars


if __name__ == '__main__':
    ping("google.com")
