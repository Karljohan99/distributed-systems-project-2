import grpc
import re
from concurrent import futures
import chain_pb2
import chain_pb2_grpc
import threading
from random import shuffle

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
        self.tail = None
        self.head = None

    def Ping(self, request, context):
        return chain_pb2.Empty()

    def CreateProcesses(self, request, context):
        for i in range(request.amount):
            self.processes.append(Process(i, self.id))
        for process in self.processes:
            print(process)
        return chain_pb2.Empty()

    def GetProcesses(self, request, context):
        processesList = []
        print(self.id)
        for process in self.processes:
            print(process)
            processesList.append(f'{self.id}-{process.id}')
        print("P-List", processesList)
        response = chain_pb2.ProcessList(processes=processesList)
        print("Response", response)
        # response.processes = processesList
        return response

    def UpdateProcesses(self, request, context):
        print("krt")
        print(len(self.processes))
        print(request.current)
        self.head = request.head
        self.tail = request.tail
        current = self.processes[int(request.current.split("-")[1])]
        current.previous = request.previous
        current.next = request.next
        return chain_pb2.Empty()


def get_id():
    for i in range(1, MAX_NODES + 1):
        with grpc.insecure_channel(f'localhost:{i}' if LOCALHOST else f'192.168.76.5{i}:50051') as channel:
            stub = chain_pb2_grpc.UserStub(channel)
            try:
                stub.Ping(chain_pb2.Empty())
            except:
                return i
    return None


def check_command_correctness(command):
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


def createChain(node_id):
    processes = getProcessesFromServers(node_id)
    shuffle(processes)
    # [1-1, 2-1, 2-2]
    # [2-1, 1-1, 2-2]
    head = processes[0]
    tail = processes[-1]
    for i, pr in enumerate(processes):
        current = processes[i]
        if i == 0:
            previous = None
        else:
            previous = processes[i - 1]
        if i == len(processes) - 1:
            next = None
        else:
            next = processes[i + 1]
        nodeId = pr.split("-")[0]
        process_id = pr.split("-")[1]
        if nodeId == node_id:
            continue
        with grpc.insecure_channel(f'localhost:{nodeId}' if LOCALHOST else f'192.168.76.5{nodeId}:50051') as channel:
            stub = chain_pb2_grpc.UserStub(channel)
            response = stub.UpdateProcesses(
                chain_pb2.UpdateMessage(previous=previous, current=current, next=next, head=head, tail=tail))


def ProcessCommand(node_id, input):
    if not check_command_correctness(input):
        return (False, "[Command] - Unknown command")
    cmd = input.split(" ")
    base_cmd = cmd[0].strip()
    try:
        params = cmd[1].strip()
    except:
        params = None
    match base_cmd:
        case "Local-store-ps":
            with grpc.insecure_channel(
                    f'localhost:{node_id}' if LOCALHOST else f'192.168.76.5{node_id}:50051') as channel:
                stub = chain_pb2_grpc.UserStub(channel)
                stub.CreateProcesses(chain_pb2.CreateProcessesMessage(amount=int(params)))
        case "Create-chain":
            createChain(node_id)
            print("todo")
        case "List-chain":
            getProcessesFromServers(node_id)
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


def getProcessesFromServers(node_id):
    allProcesses = []
    for i in range(1, MAX_NODES + 1):
        with grpc.insecure_channel(f'localhost:{i}' if LOCALHOST else f'192.168.76.5{i}:50051') as channel:
            stub = chain_pb2_grpc.UserStub(channel)
            response = stub.GetProcesses(chain_pb2.Empty())
            print(response.processes)
            allProcesses.extend(response.processes)
    print("All processes", allProcesses)
    return allProcesses


def serve():
    node_id = get_id()
    print(node_id)
    if node_id is None:
        print("No room available!")
        return
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chain_pb2_grpc.add_UserServicer_to_server(
        ChainServicer(node_id), server)
    server.add_insecure_port(f'localhost:{node_id}' if LOCALHOST else f'192.168.76.5{node_id}:50051')
    server.start()
    print(f"Server started listening on port 50051")
    while True:
        userInput = input(f"Command > ")
        ProcessCommand(node_id, userInput)


if __name__ == '__main__':
    serve()
