import grpc
import re
from concurrent import futures
import chain_pb2
import chain_pb2_grpc


MAX_NODES = 3 #Maximum number of nodes allowed
LOCALHOST = True #Set True to run all Nodes locally

class ChainServicer(chain_pb2_grpc.UserServicer):
    def __init__(self, id):
        self.id = id

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

    def ProcessCommand(self, input):
        if not self.check_command_correctness(input):
            return (False, "[Command] - Unknown command")
        cmd = input.split(" ")
        base_cmd = cmd[0].strip()
        match base_cmd:
            case "Local-store-ps":
                print("todo")
            case "Create-chain":
                print("todo")
            case "List-chain":
                print("todo")
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
    for i in range(1, MAX_NODES+1):
        with grpc.insecure_channel(f'localhost:{i}' if LOCALHOST else f'192.168.76.5{i}:50051') as channel:
            stub = chain_pb2_grpc.UserStub(channel)
            try:
                stub.Ping(chain_pb2.Empty())
            except:
                return i
    return None

def serve():
    id = get_id()
    node = ChainServicer(id)
    print("hey")
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