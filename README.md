# distributed-systems-project-2
An online book shop that implements chain replication

Each computer can act as a Node.\
Each node has k processes.\
When chain is created, processes have previous and next processes. Write commands are done from chain head to tail and reads are done in the tail (consultating with head). Each process has all the books that have inserted.\
From each node it's possible to enter commands to change data in chain, read current status, change chain. \

We followed project's description to implement the model (see PDF for more details).

### System blueprint
![Blueprint](blueprint.png)
