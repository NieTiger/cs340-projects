from typing import Dict

from simulator.node import Node


class Distance_Vector_Node(Node):
    def __init__(self, id):
        super().__init__(id)
        # Cost and next hop for every destination
        self.dv: Dict = {}

    # Return a string
    def __str__(self):
        return f < "Node {self.id}>"

    # Fill in this function
    def link_has_been_updated(self, neighbor, latency):
        # latency = -1 if delete a link
        if latency < 0:
            del self.dv[neighbor]
            # send to neighbors
        else:
            self.dv[neighbor] = latency
        # send to neighbors

    # Fill in this function
    def process_incoming_routing_message(self, m):
        pass

    # Return a neighbor, -1 if no path to destination
    def get_next_hop(self, destination):
        return -1
