import grpc
import re

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

def ProcessCommand(input):
    if not check_command_correctness(input):
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

def serve():
    while True:
        userInput = input(f"Command > ")
        ProcessCommand(userInput)

if __name__ == '__main__':
    serve()