"python3 sim.py DISTANCE_VECTOR demo.event"
from logging import root
from typing import Dict, List, NamedTuple
import copy
import json
import math

from simulator.node import Node
from adj_graph import Edge, Neighbor


class DV_Node(NamedTuple):
    cost: int
    path: List[int]
    

def bellman_ford(nodes, edges: List[Edge], root):
    dist = {i: math.inf for i in nodes}
    prev = {i: None for i in nodes}
    
    dist[root] = 0

    for _ in range(len(nodes)):
        for edge in edges:
            alt = dist[node1]



class Distance_Vector_Node(Node):
    def __init__(self, id):
        super().__init__(id)
        # Cost and next hop for every destination
        # destination -> ⟨cost, path⟩
        self.dv: Dict[int, DV_Node] = {}

        # neighbor_id -> neighbor's dv
        self.neighbors_dv: Dict = {}
        # neighbor_id -> cost
        self.outbound_links: Dict[int, int] = {}


    # Return a string
    def __str__(self):
        return f"<Node {self.id}, dv={self.dv}, oblinks={self.outbound_links}, neighbors_dv={self.neighbors_dv}>"
    
    def update_dv(self) -> None:
        dv = {}
        for nid, ndv in self.neighbors_dv.items():
            outbound_cost = self.outbound_links[nid]

            for dest, (cost, path) in ndv.items():
                if self.id in path:
                    continue
                curr_node = dv.get(dest)
                if curr_node and (cost + outbound_cost) >= curr_node.cost:
                    # existing node in DV is optimal
                    pass
                else:
                    # new node or a new shorter path found
                    new_p = copy.deepcopy(path)
                    new_p.append(nid)
                    dv[dest] = DV_Node(cost + outbound_cost, new_p)

        # if dv changes, send to neighbors
        _changed = False
        for dest, (cost, path) in dv.items():
            node = self.dv.get(dest)
            if node and node.cost == cost and node.path == path:
                pass
            else:
                _changed = True
                break

        for dest, (cost, path) in self.dv.items():
            node = dv.get(dest)
            if node and node.cost == cost and node.path == path:
                pass
            else:
                _changed = True
                break

        if _changed:
            breakpoint()
            self.dv = dv
            self.send_to_neighbors(json.dumps((self.id, self.dv)))

    # Fill in this function
    def link_has_been_updated(self, neighbor, latency):
        # latency = -1 if delete a link
        if latency >= 0:
            # create/update link to new node
            self.dv[neighbor] = (latency, [neighbor])
            self.outbound_links[neighbor] = latency
        else: # negative latency
            if neighbor in self.dv:
                # remove existing node
                del self.dv[neighbor]
                del self.outbound_links[neighbor]
            else: 
                return

        self.update_dv()

    # Fill in this function
    def process_incoming_routing_message(self, m):
        from_id, dv = json.loads(m)
        
        self.neighbors_dv[from_id] = dv

        self.update_dv()

    # Return a neighbor, -1 if no path to destination
    def get_next_hop(self, destination):
        if destination in self.dv:
            return self.dv[destination][1][-1]
        return -1

