from typing import Dict, NamedTuple, List
import json

from simulator.node import Node

from adj_graph import Edge, Neighbor, Graph


# For each neighbour we need to keep track of
# neighbor_id
# latency
# seq_n <- for the update of a specific link


class LinkStateBroadcastMsg(Edge):
    pass


class Link_State_Node(Node):
    def __init__(self, id):
        super().__init__(id)

        # graph - adjacency list
        self.graph: Graph = Graph()
        
        # reachable - ReachableNode : NextHop
        self.reachable: Map[int, int] = {}

    # Return a string
    def __str__(self):
        return f"<Node {self.id}>"

    # Fill in this function
    def link_has_been_updated(self, neighbor, latency):

        broadcast_msg: str = ""

        if latency == -1:
            # delete the edge
            e: Edge = self.graph.get_edge(self.id, neighbor)
            broadcast_msg = json.dumps(Edge(
                node1=self.id,
                node2=neighbor,
                seq_n=e.seq_n,
                latency=-1,
            ))

            self.graph.remove_edge(self.id, neighbor)
        else:
            try:
                e: Edge = self.graph.get_edge(self.id, neighbor)
            except ValueError:
                # new edge
                self.graph.add_edge(self.id, neighbor, latency, 0)
                e: Edge = self.graph.get_edge(self.id, neighbor)
            else:
                # update edge
                self.graph.update_edge(self.id, neighbor, latency, e.seq_n + 1)

            broadcast_msg = json.dumps(e)

        # TODO: RUN DIJKSTRA

        # BROADCAST THIS MSG
        self.send_to_neighbors(broadcast_msg)
        self.logging.debug(
            "link update, neighbor %d, latency %d, time %d"
            % (neighbor, latency, self.get_time())
        )

    # Fill in this function
    def process_incoming_routing_message(self, m):
        msg_obj = LinkStateBroadcastMsg(*json.loads(m))
        # check if node1 or node2 is in the adj list
        if msg_obj.node1 in self.neighbors:
            pass
        elif msg_obj.node2 in self.neighbors:
            pass
        else:
            # new edge
            pass

        # TODO: RUN DJIKSTRA

    # Return a neighbors, -1 if no path to destination
    def get_next_hop(self, destination):
        return self.reachable.get(destination, -1)
