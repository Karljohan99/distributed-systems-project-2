import grpc
import re
import time
from concurrent import futures
import chain_pb2
import chain_pb2_grpc
from random import shuffle

MAX_NODES = 3  # Maximum number of nodes allowed
LOCALHOST = False  # Set True to run all Nodes locally


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
        self.timeout = 1
        self.pendingRemoval = None
        self.pendingRemovalStr = None
        self.operationCount = 0

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
        for process in self.processes:
            processesList.append(f'{self.id}-{process.id}')
        response = chain_pb2.ProcessList(processes=processesList)
        return response

    def UpdateProcesses(self, request, context):
        self.head = request.head
        self.tail = request.tail
        current = self.processes[int(request.current.split("-")[1])]
        current.previous = request.previous
        current.next = request.next
        return chain_pb2.Empty()

    def GetHeadAndTail(self, request, context):
        return chain_pb2.HeadAndTailMessage(head=self.head, tail=self.tail)

    def ListChain(self, request, context):
        if request.path == "":
            request.path += "(Head) "
            goToNode = self.head.split("-")[0]
            if goToNode != self.id:
                with grpc.insecure_channel(
                        f'localhost:5005{goToNode}' if LOCALHOST else f'192.168.76.5{goToNode}:50051') as channel:
                    stub = chain_pb2_grpc.UserStub(channel)
                    response = stub.ListChain(chain_pb2.ListChainMessage(path=request.path, next=self.head))
                    return chain_pb2.ChainResult(chain=request.path + response.chain)
            else:
                current = self.processes[int(self.head.split("-")[1])]
                goToNode = current.next.split("-")[0]
                request.path += current.next + " -> "
                with grpc.insecure_channel(
                        f'localhost:5005{goToNode}' if LOCALHOST else f'192.168.76.5{goToNode}:50051') as channel:
                    stub = chain_pb2_grpc.UserStub(channel)
                    response = stub.ListChain(chain_pb2.ListChainMessage(path=request.path, next=current.next))
                    return chain_pb2.ChainResult(chain=request.path + response.chain)
        else:
            current = self.processes[int(request.next.split("-")[1])]
            request.path += request.next + " -> "
            if current.next:
                goToNode = current.next.split("-")[0]
                with grpc.insecure_channel(
                        f'localhost:5005{goToNode}' if LOCALHOST else f'192.168.76.5{goToNode}:50051') as channel:
                    stub = chain_pb2_grpc.UserStub(channel)
                    response = stub.ListChain(chain_pb2.ListChainMessage(path=request.path, next=current.next))
                    return chain_pb2.ChainResult(chain=request.path + response.chain)
            else:
                return chain_pb2.ChainResult(chain=request.path[:-3] + "(Tail)")

    def WriteOperation(self, request, context):
        process = self.processes[request.process]
        process.books[request.book_name] = (request.price, False)
        time.sleep(self.timeout)
        self.updateOperationCount()

        if process.next != "":
            next_node = int(process.next.split("-")[0])
            next_prc = int(process.next.split("-")[1])
            with grpc.insecure_channel(
                    f'localhost:5005{next_node}' if LOCALHOST else f'192.168.76.5{next_node}:50051') as channel:
                stub = chain_pb2_grpc.UserStub(channel)
                result = stub.WriteOperation(
                    chain_pb2.WriteOperationMessage(book_name=request.book_name, price=request.price, process=next_prc))
                if result.success:
                    process.books[request.book_name] = (process.books[request.book_name][0], True)
                    nameAndPrice = f"{request.book_name} = {process.books[request.book_name][0]} EUR"
                    return chain_pb2.WriteOperationResult(success=True, bookNameAndPrice=nameAndPrice)
                else:
                    return chain_pb2.WriteOperationResult(success=False, bookNameAndPrice="Write failed!")
        else:
            nameAndPrice = f"{request.book_name} = {process.books[request.book_name][0]} EUR"
            process.books[request.book_name] = (process.books[request.book_name][0], True)
            return chain_pb2.WriteOperationResult(success=True, bookNameAndPrice=nameAndPrice)

    def ListBooks(self, request, context):
        tail = self.processes[request.process]
        book_list = ""
        i = 1
        for name, (price, _) in tail.books.items():
            book_list += f"{i}) {name} = {price} EUR\n"
            i += 1
        return chain_pb2.ListBooksResult(booksList=book_list)

    def ReadOperation(self, request, context):
        process = self.processes[request.process]
        price = process.books.get(request.book_name, (-1.0, True))[0]
        self.updateOperationCount()

        # Consult head
        if self.head != f"{self.id}-{request.process}":
            head_node = int(self.head.split("-")[0])
            head_prc = int(self.head.split("-")[1])
            with grpc.insecure_channel(
                    f'localhost:5005{head_node}' if LOCALHOST else f'192.168.76.5{head_node}:50051') as channel:
                stub = chain_pb2_grpc.UserStub(channel)
                response = stub.ReadOperation(
                    chain_pb2.ReadOperationMessage(book_name=request.book_name, process=head_prc))
                price = response.bookPrice

        return chain_pb2.ReadOperationResult(bookPrice=price)

    def TimeOut(self, request, context):
        self.timeout = request.timeout
        return chain_pb2.Empty()

    def DataStatus(self, request, context):
        head = self.processes[request.process]
        i = 1
        cln = lambda clean: "clean" if clean else "dirty"
        status = ""
        for name, (_, clean) in head.books.items():
            status += f"{i}) {name} - {cln(clean)}\n"
            i += 1
        return chain_pb2.DataStatusResult(booksStatus=status)

    def updateOperationCount(self):
        self.operationCount += 1
        if self.operationCount > 5:
            self.pendingRemoval = None
            self.pendingRemovalStr = None

    def RemoveHead(self, request, context):
        newHeadId = int(request.newHead.split("-")[0])
        newHeadPrc = int(request.newHead.split("-")[1])
        if newHeadId == self.id:
            self.processes[newHeadPrc].previous = None

        self.head = request.newHead
        self.pendingRemovalStr = request.head
        return chain_pb2.Empty()

    def CheckPendingRemoval(self, request, context):
        return chain_pb2.PendingStatus(isNone=self.pendingRemovalStr is None)

    def RestoreHead(self, request, context):
        head = request.head
        node = int(head.split('-')[0])
        prc = int(head.split('-')[1])
        if node == self.id:
            self.processes[prc].previous = self.pendingRemovalStr
        self.head = self.pendingRemovalStr
        self.pendingRemoval = None
        self.pendingRemovalStr = None
        self.operationCount = 0
        return chain_pb2.RestoreHeadResponse(newHead=self.head)


def get_id():
    for i in range(1, MAX_NODES + 1):
        with grpc.insecure_channel(f'localhost:5005{i}' if LOCALHOST else f'192.168.76.5{i}:50051') as channel:
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
            bool(re.fullmatch('Write-operation <".+", \d+.\d+>', command)) or
            command == 'List-books' or
            bool(re.fullmatch('Read-operation ".+"', command)) or
            bool(re.fullmatch('Time-out \d+', command)) or
            command == 'Data-status' or
            command == 'Remove-head' or
            command == 'Restore-head')


def createChain(node_id):
    processes = getProcessesFromServers(node_id)
    shuffle(processes)
    print("Shuffled", processes)
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
        with grpc.insecure_channel(
                f'localhost:5005{nodeId}' if LOCALHOST else f'192.168.76.5{nodeId}:50051') as channel:
            stub = chain_pb2_grpc.UserStub(channel)
            response = stub.UpdateProcesses(
                chain_pb2.UpdateMessage(previous=previous, current=current, next=next, head=head, tail=tail))
    return head, tail


def getChain():
    with grpc.insecure_channel(f'localhost:5005{1}' if LOCALHOST else f'192.168.76.5{1}:50051') as channel:
        stub = chain_pb2_grpc.UserStub(channel)
        response = stub.ListChain(chain_pb2.ListChainMessage(path=""))
        chainText = response.chain
        response = "(Head)" + chainText.split("(Head)")[-1]
        return response


def getHeadandTail(node_id):
    with grpc.insecure_channel(f'localhost:5005{node_id}' if LOCALHOST else f'192.168.76.5{node_id}:50051') as channel:
        stub = chain_pb2_grpc.UserStub(channel)
        response = stub.GetHeadAndTail(chain_pb2.Empty())
        return response.head, response.tail


def removeHead():
    chain = getChain()
    head = chain.split(' ')[1]
    print(head)
    newHead = chain.split(' ')[3]
    for i in range(1, MAX_NODES + 1):
        with grpc.insecure_channel(f'localhost:5005{i}' if LOCALHOST else f'192.168.76.5{i}:50051') as channel:
            stub = chain_pb2_grpc.UserStub(channel)
            stub.RemoveHead(chain_pb2.RemoveHeadMessage(head=head, newHead=newHead))

    print(getChain())
    return newHead


def restoreHead():
    chain = getChain()
    head = chain.split(' ')[1]
    node = int(head.split('-')[0])
    prc = int(head.split('-')[1])
    with grpc.insecure_channel(f'localhost:5005{node}' if LOCALHOST else f'192.168.76.5{node}:50051') as channel:
        stub = chain_pb2_grpc.UserStub(channel)
        response = stub.CheckPendingRemoval(chain_pb2.Empty())
    if not response.isNone:
        for i in range(1, MAX_NODES + 1):
            with grpc.insecure_channel(f'localhost:5005{i}' if LOCALHOST else f'192.168.76.5{i}:50051') as channel:
                stub = chain_pb2_grpc.UserStub(channel)
                response = stub.RestoreHead(chain_pb2.RestoreHeadMessage(head=head))
        if response.newHead is not None:
            return response.newHead
    return head


def ProcessCommand(node_id, input, head, tail):
    if not check_command_correctness(input):
        print("[Command] - Unknown command")
    cmd = input.split(" ")
    base_cmd = cmd[0].strip()
    try:
        params = " ".join(cmd[1:]).strip()
    except:
        params = None
    match base_cmd:
        case "Local-store-ps":
            with grpc.insecure_channel(
                    f'localhost:5005{node_id}' if LOCALHOST else f'192.168.76.5{node_id}:50051') as channel:
                stub = chain_pb2_grpc.UserStub(channel)
                stub.CreateProcesses(chain_pb2.CreateProcessesMessage(amount=int(params)))
        case "Create-chain":
            try:
                return createChain(node_id)
            except:
                print("There might be no processes.")
        case "List-chain":
            try:
                response = getChain()
                print(response)
            except:
                print("There is no chain.")
        case "Write-operation":
            try:
                if head is None or tail is None:
                    head, tail = getHeadandTail(node_id)

                search = re.search('<"(.+)", (\d+.\d+)>', params, re.IGNORECASE)
                book_name = search.group(1)
                price = float(search.group(2))
                head_node = int(head.split("-")[0])
                head_prc = int(head.split("-")[1])
                with grpc.insecure_channel(
                        f'localhost:5005{head_node}' if LOCALHOST else f'192.168.76.5{head_node}:50051') as channel:
                    stub = chain_pb2_grpc.UserStub(channel)
                    response = stub.WriteOperation(
                        chain_pb2.WriteOperationMessage(book_name=book_name, price=price, process=head_prc))
                print(response.bookNameAndPrice)
            except:
                print("There is no chain.")

        case "List-books":
            try:
                if head is None or tail is None:
                    head, tail = getHeadandTail(node_id)
                tail_node = int(tail.split("-")[0])
                tail_prc = int(tail.split("-")[1])
                with grpc.insecure_channel(
                        f'localhost:5005{tail_node}' if LOCALHOST else f'192.168.76.5{tail_node}:50051') as channel:
                    stub = chain_pb2_grpc.UserStub(channel)
                    response = stub.ListBooks(chain_pb2.ListBooksMessage(process=tail_prc))
                    print(response.booksList)
            except:
                print("There is no chain.")
        case "Read-operation":
            try:
                if head is None or tail is None:
                    head, tail = getHeadandTail(node_id)

                search = re.search('"(.+)"', params, re.IGNORECASE)
                book_name = search.group(1)
                tail_node = int(tail.split("-")[0])
                tail_prc = int(tail.split("-")[1])
                with grpc.insecure_channel(
                        f'localhost:5005{tail_node}' if LOCALHOST else f'192.168.76.5{tail_node}:50051') as channel:
                    stub = chain_pb2_grpc.UserStub(channel)
                    response = stub.ReadOperation(chain_pb2.ReadOperationMessage(book_name=book_name, process=tail_prc))
                    if response.bookPrice > 0:
                        print(f"{response.bookPrice} EUR")
                    else:
                        print("Not yet in the stock")
            except:
                print("There is no chain.")
        case "Time-out":
            try:
                for i in range(1, MAX_NODES + 1):
                    with grpc.insecure_channel(
                            f'localhost:5005{i}' if LOCALHOST else f'192.168.76.5{i}:50051') as channel:
                        stub = chain_pb2_grpc.UserStub(channel)
                        stub.TimeOut(chain_pb2.TimeOutMessage(timeout=int(params)))
            except:
                print("Setting time-out failed.")
        case "Data-status":
            try:
                if head is None or tail is None:
                    head, tail = getHeadandTail(node_id)
                head_node = int(head.split("-")[0])
                head_prc = int(head.split("-")[1])
                with grpc.insecure_channel(
                        f'localhost:5005{head_node}' if LOCALHOST else f'192.168.76.5{head_node}:50051') as channel:
                    stub = chain_pb2_grpc.UserStub(channel)
                    response = stub.DataStatus(chain_pb2.DataStatusMessage(process=head_prc))
                    print(response.booksStatus)
            except:
                print("Failed to get data-status.")
        case "Remove-head":
            try:
                head = removeHead()
            except:
                print("There is no head to remove.")
        case "Restore-head":
            try:
                head = restoreHead()
            except:
                print("There is no head to restore.")
    return head, tail


def getProcessesFromServers(node_id):
    allProcesses = []
    for i in range(1, MAX_NODES + 1):
        with grpc.insecure_channel(f'localhost:5005{i}' if LOCALHOST else f'192.168.76.5{i}:50051') as channel:
            stub = chain_pb2_grpc.UserStub(channel)
            response = stub.GetProcesses(chain_pb2.Empty())
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
    server.add_insecure_port(f'localhost:5005{node_id}' if LOCALHOST else f'192.168.76.5{node_id}:50051')
    server.start()
    # print(f"Server started listening on port 50051")
    head, tail = None, None
    while True:
        userInput = input(f"Node-{node_id} > ")
        head, tail = ProcessCommand(node_id, userInput, head, tail)


if __name__ == '__main__':
    serve()
