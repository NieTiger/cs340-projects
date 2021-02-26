from typing import NamedTuple
import json

from simulator.node import Node


# For each neighbour we need to keep track of
# neighbor_id
# latency
# seq_n <- for the update of a specific link

class LinkStateBroadcastMsg(NamedTuple):
    seq_n: int
    latency: int
    node1: int
    node2: int


class Link_State_Node(Node):
    def __init__(self, id):
        super().__init__(id)

        # also keep track of neigbours seq_n
        self.neighbors = {}  # mapping to {seq_n, latency, dest}
        
        # adjacency list
        # map from vertex to a list of (neighbor, latency, seq_n)
        self.graph

        # self.neighbors = self.graph[self.id]

    # Return a string
    def __str__(self):
        return "Rewrite this function to define your node dump printout"

    # Fill in this function
    def link_has_been_updated(self, neighbor, latency):

        broadcast_msg: str = ""

        if latency == -1 and neighbor in self.neighbors:
            # latency = -1 if delete a link
            msg_obj = LinkStateBroadcastMsg(node1=self.id, node2=neighbor, latency=latency, 
                seq_n=self.neighbors[neighbor]["seq_n"]
            )
            broadcast_msg = json.dumps(msg_obj)
            del self.neighbors[neighbor]

        elif neighbor in self.neighbors:
            # update an existing neighbor
            self.neighbors[neighbor]["latency"] = latency
            msg_obj = LinkStateBroadcastMsg(node1=self.id, node2=neighbor, latency=latency, 
                seq_n=self.neighbors[neighbor]["seq_n"]
            )
            broadcast_msg = json.dumps(msg_obj)
        else:
            # new neighbors
            self.neighbors[neighbor] = {
                "latency": latency,
                "dest": neighbors,
                "seq_n": 0,
            }
            msg_obj = LinkStateBroadcastMsg(node1=self.id, node2=neighbor, latency=latency, 
                seq_n=self.neighbors[neighbor]["seq_n"]
            )
            broadcast_msg = json.dumps(msg_obj)

        # TODO: RUN DIJKSTRA
        
        # BROADCAST THIS MSG
        self.send_to_neighbors(broadcast_msg)
        self.logging.debug('link update, neighbor %d, latency %d, time %d' % (neighbor, latency, self.get_time()))

    # Fill in this function
    def process_incoming_routing_message(self, m):
        msg_obj = LinkStateBroadcastMsg(*json.loads(m))
        msg_obj.node1
        # check if node1 or node2 is in the adj list
        if msg_obj.node1 in self.neighbors:
            pass
        elif msg_obj.node2 in self.neighbors:
            pass
        else:
            # new edge
            pass

        # TODO: RUN DIJKSTRA

    # Return a neighbors, -1 if no path to destination
    def get_next_hop(self, destination):
        return -1
