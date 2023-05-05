import grpc
import re
from concurrent import futures
import chain_pb2
import chain_pb2_grpc
import threading

MAX_NODES = 2  # Maximum number of nodes allowed
LOCALHOST = True  # Set True to run all Nodes locally


class Process():
    def __init__(self, id, chainServicerId):
        self.servicer = chainServicerId
        self.id = id
        self.books = {}
        self.previous = None
        self.next = None

    def __str__(self):
        return f'"servicer": {self.servicer}, "id": {self.id}, "books": {self.books}, "previous": {self.previous}, "next": {self.next}'

    def update_next(self, key, value):
        return None

class ChainServicer(chain_pb2_grpc.UserServicer):
    def __init__(self, id):
        self.id = id
        self.processes = []

    def check_command_correctness(self, command):
        return (
                bool(re.fullmatch('Local-store-ps \d+', command)) or
                command == 'Create-chain' or
                command == 'List-chain' or
                bool(re.fullmatch('Write-operation <".*", \d+.\d+>', command)) or
                command == 'List-books' or
                bool(re.fullmatch('Read-operation ".+"', command)) or
                bool(re.fullmatch('Time-out \d+', command)) or
                command == 'Data-status' or
                command == 'Remove-head' or
                command == 'Restore-head')

    def createProcesses(self, amount):
        for i in range(amount):
            self.processes.append(Process(i, self.id))
        for process in self.processes:
            print(process)

    def Ping(self, request, context):
        return chain_pb2.Empty()

    def GetProcesses(self, request, context):
        processesList = []
        print(self.id)
        for process in self.processes:
            print(process)
            processesList.append(str(process))
        print(processesList)
        response = chain_pb2.ProcessList(processes=processesList)
        print(response)
        #response.processes = processesList
        return response

    def getProcessesFromServers(self):
        allProcesses = []
        for i in range(1, MAX_NODES + 1):
            with grpc.insecure_channel(f'localhost:{i}' if LOCALHOST else f'192.168.76.5{i}:50051') as channel:
                stub = chain_pb2_grpc.UserStub(channel)
                response = stub.GetProcesses(chain_pb2.Empty())
                print(response.processes)
                allProcesses.append(response)
        print(allProcesses)

    def ProcessCommand(self, input):
        if not self.check_command_correctness(input):
            return (False, "[Command] - Unknown command")
        cmd = input.split(" ")
        base_cmd = cmd[0].strip()
        try:
            params = cmd[1].strip()
        except:
            params = None
        match base_cmd:
            case "Local-store-ps":
                self.createProcesses(int(params))
            case "Create-chain":
                print("todo")
            case "List-chain":
                self.getProcessesFromServers()
            case "Write-operation":
                print("todo")
            case "List-books":
                print("todo")
            case "Read-operation":
                print("todo")
            case "Time-out":
                print("todo")
            case "Data-status":
                print("todo")
            case "Remove-head":
                print("todo")
            case "Restore-head":
                print("todo")
        return False, "[Command] - Unknown command"


def get_id():
    for i in range(1, MAX_NODES + 1):
        with grpc.insecure_channel(f'localhost:{i}' if LOCALHOST else f'192.168.76.5{i}:50051') as channel:
            stub = chain_pb2_grpc.UserStub(channel)
            try:
                stub.Ping(chain_pb2.Empty())
            except:
                return i
    return None


def serve():
    id = get_id()
    print(id)
    node = ChainServicer(id)
    if id is None:
        print("No room available!")
        return
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chain_pb2_grpc.add_UserServicer_to_server(
        ChainServicer(id), server)
    server.add_insecure_port(f'localhost:{id}' if LOCALHOST else f'192.168.76.5{id}:50051')
    server.start()
    print(f"Server started listening on port 50051")
    while True:
        userInput = input(f"Command > ")
        node.ProcessCommand(userInput)


if __name__ == '__main__':
    serve()
