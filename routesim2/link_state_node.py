from typing import Dict, NamedTuple
import json

from simulator.node import Node

from adj_graph import Edge, Neighbor, Graph, dijkstra


# For each neighbour we need to keep track of
# neighbor_id
# latency
# seq_n <- for the update of a specific link


class LinkStateBroadcastMsg(Edge):
    pass


class Link_State_Node(Node):
    def __init__(self, id):
        super().__init__(id)
        self.logging.info("Node %d constructed", id)

        # graph - adjacency list
        self.graph: Graph = Graph()
        
        # pred - ReachableNode : NextHop
        self.pred: Dict[int, int] = {}
        
        # list of most recent routing msg for every edge in the graph
        self.routing_msgs: Dict = {}

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
                weight=-1,
            ))

            self.graph.remove_edge(self.id, neighbor)
            self.logging.info("link_has_been_updated, removing neighbor: %d, latency %d", neighbor, latency)
        else:
            try:
                e: Edge = self.graph.get_edge(self.id, neighbor)
            except ValueError:
                # new edge
                self.graph.add_edge(self.id, neighbor, latency, 0)
                e: Edge = self.graph.get_edge(self.id, neighbor)
                self.logging.info("link_has_been_updated, new neighbor: %d, latency %d", neighbor, latency)
            else:
                # update edge
                self.graph.update_edge(self.id, neighbor, latency, e.seq_n + 1)
                self.logging.info("link_has_been_updated, updating neighbor: %d, latency %d", neighbor, latency)

            broadcast_msg = json.dumps(e)
        
        # update history
        u, v = neighbor, self.id
        if u > v:
            u, v = v, u
        self.routing_msgs[(u, v)] = broadcast_msg

        for _, old_msg in self.routing_msgs.items():
            self.send_to_neighbor(neighbor, old_msg)

        # TODO: RUN DIJKSTRA
        pred, _ = dijkstra(self.graph, self.id)
        self.pred = pred

        # BROADCAST THIS MSG
        self.send_to_neighbors(broadcast_msg)
        self.logging.debug(
            "link update, neighbor %d, latency %d, time %d"
            % (neighbor, latency, self.get_time())
        )

    # Fill in this function
    def process_incoming_routing_message(self, m):
        new_edge = LinkStateBroadcastMsg(*json.loads(m))
        # check if node1 or node2 is in the adj list
        try:
            e = self.graph.get_edge(new_edge.node1, new_edge.node2)
        except ValueError:
            # new edge
            self.graph.add_edge(new_edge.node1, new_edge.node2, new_edge.weight, new_edge.seq_n)
            # propagate
            self.send_to_neighbors(m)
            self.logging.info("incoming routing msg, new edge: (%d, %d), latency %d", new_edge.node1, new_edge.node2, new_edge.weight)
        else:
            # old edge, check seq_n
            if new_edge.seq_n > e.seq_n:
                self.graph.update_edge(new_edge.node1, new_edge.node2, new_edge.weight, new_edge.seq_n)
                # propagate
                self.send_to_neighbors(m)
                self.logging.info("incoming routing msg, old edge: (%d, %d), latency %d", new_edge.node1, new_edge.node2, new_edge.weight)
            
        # update history
        u, v = new_edge.node1, new_edge.node2
        if u > v:
            u, v = v, u
        self.routing_msgs[(u, v)] = m

        # TODO: RUN DJIKSTRA
        pred, _ = dijkstra(self.graph, self.id)
        self.pred = pred
    

    # Return a neighbors, -1 if no path to destination
    def get_next_hop(self, destination):
        # return self.pred.get(destination, -1)
        v = destination
        while self.pred[v] != self.id:
            v = self.pred[v]
        return v

