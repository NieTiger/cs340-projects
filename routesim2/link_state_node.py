from typing import Dict, NamedTuple
from collections import defaultdict
import json

from simulator.node import Node

from adj_graph import Edge, Neighbor, Graph, dijkstra

# Broadcast msg format
"""
broadcast_msg = {
    "from_id": INT,
    "n1": INT,
    "n2": INT,
    "weight": INT,
    "seq_n": INT,
}
"""


class Link_State_Node(Node):
    def __init__(self, id):
        super().__init__(id)
        self.logging.info("Node %d constructed", id)

        # graph - adjacency list
        self.graph: Graph = Graph()

        # pred - ReachableNode : NextHop
        self.pred: Dict[int, int] = {}

        # dict of most recent routing msg for every edge in the graph
        self.routing_msgs: Dict = {}

        self.link_seq_n: Dict = defaultdict(int)

    # Return a string
    def __str__(self):
        return f"<Node {self.id}, Reachable Nodes and next hops: {self.pred}>"

    # Fill in this function
    def link_has_been_updated(self, neighbor, latency):
        broadcast_msg: dict = {}
        lset = frozenset((self.id, neighbor))
        self.link_seq_n[lset] += 1

        if latency < 0:
            # delete the edge
            self.graph.remove_edge(self.id, neighbor)
            # self.logging.info(
            # "link_has_been_updated, removing neighbor: %d, latency %d",
            # neighbor,
            # latency,
            # )
        else:
            if self.graph.has_edge(self.id, neighbor):
                # update edge
                self.graph.update_edge(self.id, neighbor, latency)
                # self.logging.info(
                # "link_has_been_updated, updating neighbor: %d, latency %d",
                # neighbor,
                # latency,
                # )
            else:
                # new edge
                self.graph.add_edge(self.id, neighbor, latency)
                # self.logging.info(
                # "link_has_been_updated, new neighbor: %d, latency %d",
                # neighbor,
                # latency,
                # )

                for _, old_msg in self.routing_msgs.items():
                    self.send_to_neighbor(neighbor, json.dumps(old_msg))

        broadcast_msg = {
            "from_id": self.id,
            "n1": self.id,
            "n2": neighbor,
            "weight": latency,
            "seq_n": self.link_seq_n[lset],
        }
        self.routing_msgs[lset] = broadcast_msg

        # TODO: RUN DIJKSTRA
        pred, _ = dijkstra(self.graph, self.id)
        self.pred = pred

        # BROADCAST THIS MSG
        # propagate
        for nbr in self.graph.get_neighbors(self.id):
            if nbr.id != neighbor:
                self.send_to_neighbor(nbr.id, json.dumps(broadcast_msg))
        self.logging.debug(
            "link update, neighbor %d, latency %d, time %d"
            % (neighbor, latency, self.get_time())
        )

    # Fill in this function
    def process_incoming_routing_message(self, m):
        # self.logging.info("new msg")
        msg = json.loads(m)
        from_id = msg["from_id"]
        msg["from_id"] = self.id
        lset = frozenset((msg["n1"], msg["n2"]))

        old_msg = self.routing_msgs.get(lset)

        if old_msg:
            if old_msg["seq_n"] > msg["seq_n"]:
                # Seen this already lmao
                # send updated msg back
                self.send_to_neighbor(from_id, json.dumps(old_msg))
                return
            elif old_msg["seq_n"] < msg["seq_n"]:
                # new packet, old edge
                if msg["weight"] < 0:
                    self.graph.remove_edge(msg["n1"], msg["n2"])
                else:
                    self.graph.update_edge(msg["n1"], msg["n2"], msg["weight"])

                # propagate
                for nbr in self.graph.get_neighbors(self.id):
                    if nbr.id != from_id:
                        self.send_to_neighbor(nbr.id, json.dumps(msg))
        else:
            # new edge
            if msg["weight"] >= 0:
                self.graph.add_edge(msg["n1"], msg["n2"], msg["weight"])

            # propagate
            for nbr in self.graph.get_neighbors(self.id):
                if nbr.id != from_id:
                    self.send_to_neighbor(nbr.id, json.dumps(msg))

        # update history
        self.routing_msgs[lset] = msg

        pred, _ = dijkstra(self.graph, self.id)
        self.pred = pred

    # Return a neighbor, -1 if no path to destination
    def get_next_hop(self, destination):
        # return self.pred.get(destination, -1)
        if destination not in self.pred:
            return -1

        v = destination
        while self.pred[v] != self.id and self.pred[v] is not None:
            v = self.pred[v]

        return v if self.pred[v] == self.id else -1
