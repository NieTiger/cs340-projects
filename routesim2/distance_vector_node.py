"python3 sim.py DISTANCE_VECTOR demo.event"
from typing import Dict, List, NamedTuple, Tuple
import copy
import json

from simulator.node import Node


class DV_Node(NamedTuple):
    cost: int
    path: List[int]
    

class Distance_Vector_Node(Node):
    def __init__(self, id):
        super().__init__(id)
        # Cost and next hop for every destination
        # destination -> ⟨cost, path⟩
        self.dv: Dict[int, DV_Node] = {}

        # neighbor_id -> (seq_n, neighbor's dv)
        self.neighbors_dv: Dict[int, Tuple(int, DV_Node)] = {}
        # neighbor_id -> cost
        self.outbound_links: Dict[int, int] = {}

    # Return a string
    def __str__(self):
        return f"<Node {self.id}, dv={self.dv}, oblinks={self.outbound_links}, neighbors_dv={self.neighbors_dv}>"

    def update_dv(self) -> None:
        dv: Dict[int, DV_Node] = {}
        for nid, (_, ndv) in self.neighbors_dv.items():
            outbound_cost = self.outbound_links[nid]

            for dest, (cost, path) in ndv.items():
                if self.id in path or nid in path:
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

        for nid, cost in self.outbound_links.items():
            if not nid in dv or dv[nid].cost > cost:
                dv[nid] = DV_Node(cost, [nid])

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
            self.dv = dv
            self.send_to_neighbors(json.dumps((self.id, self.get_time(), self.dv)))

    # Fill in this function
    def link_has_been_updated(self, neighbor, latency):
        if latency >= 0:
            # create/update link to new node
            self.outbound_links[neighbor] = latency
        elif neighbor in self.outbound_links:
            # remove existing node
            del self.outbound_links[neighbor], self.neighbors_dv[neighbor]
        else:
            return

        self.update_dv()

    # Fill in this function
    def process_incoming_routing_message(self, m):
        _from_id, _timestamp, _dv = json.loads(m)
        from_id, timestamp = int(_from_id), int(_timestamp)

        if from_id not in self.outbound_links:
            # make sure is a neighbor
            return
        
        if from_id in self.neighbors_dv and self.neighbors_dv[from_id][0] >=  timestamp:
            return

        dv = {int(nid): DV_Node(*node) for nid, node in _dv.items()}
        self.neighbors_dv[from_id] = (timestamp, dv)
        self.update_dv()

    # Return a neighbor, -1 if no path to destination
    def get_next_hop(self, destination):
        if destination in self.dv:
            return self.dv[destination].path[-1]
        breakpoint()
        return -1
