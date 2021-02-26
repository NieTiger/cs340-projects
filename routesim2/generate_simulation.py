import argparse
import datetime
import math
import random


MAX_LATENCY = 10


def random_weight():
    return random.randint(1, MAX_LATENCY)


def del_node(links, removed, file, link_time, node, time):
    change = random.randint(0, 100)
    if change <= 5:
        for t in range(link_time + 1, time):
            # link change events are a poisson process.
            # we want the time between events to be roughly 10 * MAX_LATENCY
            if 0 == random.randint(0, 10 * MAX_LATENCY):
                if len(links) > 0:
                    removed.append(node)
                    file.write("{} DELETE_NODE {}\n".format(link_time + 1, node))
                    temp = []
                    for l in links:
                        if not (l[0] == node or l[1] == node):
                            temp.append(l)
                    links.clear()
                    links.extend(temp)
                    return -1, t + 1
                break
    return 1, link_time


def del_link(links, file, link_time, time):
    change = random.randint(0, 100)
    if change <= 10:
        for t in range(link_time + 1, time):
            # link change events are a poisson process.
            # we want the time between events to be roughly 10 * MAX_LATENCY
            if 0 == random.randint(0, 10 * MAX_LATENCY):
                if len(links) > 0:
                    link_rem = random.choice(links)
                    links.remove(link_rem)
                    file.write("%d DELETE_LINK %d %d\n" % (link_time + 1, link_rem[0], link_rem[1]))
                    return t + 1
                break
    return link_time


# It appears CHANGE_NODE is not used anymore
def change_node(n, node, file, links):
    change = random.randint(0, 100)
    if change <= 10:
        if node >= n:
            new_i = node + 1
        else:
            new_i = n
        file.write("0 CHANGE_NODE {} {}\n".format(node, new_i))
        for l in links:
            new_l = l
            if l[0] == node:
                new_l = (new_i, l[1], l[2])
            elif l[1] == node:
                new_l = (l[0], new_i, l[2])

            links.remove(l)
            links.append(new_l)
        return new_i
    return node


def add_node(removed, link_time, file, nxt):
    change = random.randint(0, 100)
    if change <= 20:
        # They won't be testing reusing a node

        # if change <= 10 and len(removed) > 0:
        #     node = random.choice(removed)
        #     removed.remove(node)
        # else:
        node = nxt
        nxt += 1
        file.write("{} ADD_NODE {}\n".format(link_time, node))
    return nxt


def add_link(n, src, removed, links, link_time, file):
    neighbor = None
    timeout = 20
    count = 0
    while True:
        while neighbor is None:
            offset = int(math.floor(math.log(n,2)))
            val = random.randint(max(0, src - offset), min(n - 1, src + offset))
            if val not in removed:
                neighbor = val
        if src in removed:
            stop = 0
        link = (src, neighbor, random_weight())
        already_exists = any([(l[0] == src and l[1] == neighbor) or (l[0] == neighbor and l[1] == src) for l in links])
        if already_exists or src == neighbor:
            count += 1
            if count >= timeout:
                return link_time
            continue
        links.extend([link])
        file.write("%d ADD_LINK %d %d %d\n" % ((link_time,) + link))
        link_time += 1
        break
    return link_time


def bfs(links, islands, nodes):
    while len(nodes) > 0:
        curr = next(iter(nodes))
        queue = [curr]
        island = set([])
        while len(queue) > 0:
            curr = queue.pop(0)
            island.add(curr)
            if curr in nodes:
                nodes.remove(curr)
                for i in links:
                    if curr == i[0]:
                        queue.append(i[1])
                    elif curr == i[1]:
                        queue.append(i[0])
        islands.add(tuple(island))
    return islands




def generate_simulation(n, degree, time, filename):
    n *= 1.5
    n = int(n)
    nxt = n + 1
    time *= 2
    if degree > math.log(n,2)-1:
        raise Exception("Degree must be smaller than log(n) where n is the number of nodes.")

    links = []
    removed = []

    print("writing %s.event" % filename)
    link_time = 1
    with open("%s.event" % filename, "w") as file:
        # create nodes
        for i in range(n):
            file.write("0 ADD_NODE %d\n" % i)
        # create random edges for each node
        for i in range(n):
            # don't make links truly random, favor nodes with nearby indexes

            res, link_time = del_node(links, removed, file, link_time, i, time)
            if res == -1:
                continue

            possible_neighbors = []
            for j in range(int(math.floor(math.log(n,2)))):
                offset = 1<<j
                offset *= 1.5
                offset = int(offset)
                for neighbor in [i+offset, i-offset]:
                    if neighbor >= 0 and neighbor < n and neighbor not in removed:
                        already_exists = any([(l[0] == i and l[1] == neighbor) or (l[0] == neighbor and l[1] == i) for l in links])
                        if not already_exists:
                            possible_neighbors.append(neighbor)
            # choose random links
            for j in range(min(degree, len(possible_neighbors))):
                if link_time > time // 2:
                    break

                neighbor = random.choice(possible_neighbors)
                possible_neighbors.remove(neighbor)

                # i = change_node(n, i, file, links)

                link_time = del_link(links, file, link_time, time)

                if i in removed or neighbor in removed:
                    stop = 0

                link = (i, neighbor, random_weight())
                links.extend([link])
                file.write("%d ADD_LINK %d %d %d\n" % ((link_time,) + link))
                link_time += 1
                # above, we actually create links at different times just in case they are duplicated

                res, link_time = del_node(links, removed, file, link_time, i, time)
                if res == -1:
                    break

            if link_time > time // 2:
                break

        # change links
        # file.write("%d DRAW_TOPOLOGY\n" % link_time);
        for t in range(link_time+1, time):
            # link change events are a poisson process.
            # we want the time between events to be roughly 10 * MAX_LATENCY
            if 0 == random.randint(0, 10 * MAX_LATENCY):
                link_to_change = random.choice(links)
                links.remove(link_to_change)
                val = random_weight()
                file.write("%d CHANGE_LINK %d %d %d\n" %
                           (t, link_to_change[0], link_to_change[1], val))
                link = (link_to_change[0], link_to_change[1], val)
                links.extend([link])

                nxt = add_node(removed, t, file, nxt)
                add_link(n, link_to_change[0], removed, links, t, file)
                # change_node(n, link_to_change[1], file, links)
                del_link(links, file, t, time)
                del_node(links, removed, file, t, link_to_change[0], time)

            link_time = t + 1

        # CODE TO ENSURE GRAPH IS CONNECTED
        nodes = set([x for x in range(nxt) if x not in removed])
        islands = set([])
        islands = bfs(links, islands, nodes)
        first = None
        for ind in islands:
            if first is None:
                first = ind[0]
                continue
            second = ind[0]
            link = (first, second, random_weight())
            file.write("%d ADD_LINK %d %d %d\n" % ((link_time,) + link))
            # link_time += 20
            first = second
        # CODE TO ENSURE GRAPH IS CONNECTED

        # file.write("%d DRAW_TOPOLOGY\n" % (link_time + 1000))

        # print routing results
        for i in set([x for x in range(nxt) if x not in removed]):
            file.write("%d DRAW_TREE %d\n" % (10*time, i))


if __name__ == "__main__":
    current_time = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')
    parser = argparse.ArgumentParser(
        description='Generate random network simulation data file (.event) for Routesim.')
    parser.add_argument('--nodes', dest='n', action='store',
                        default=20, help='number of nodes in the graph')
    parser.add_argument('--degree', dest='degree', action='store',
                        default=3, help='number of edges connected to each node')
    parser.add_argument('--time', dest='time', action='store',
                        default=1000, help='time, in seconds, to run the simulation')
    parser.add_argument('--out', dest='filename', action='store',
                        default=current_time, help='output filename prefix')
    args = parser.parse_args()
    generate_simulation(n=int(args.n), degree=int(args.degree), time=int(args.time),
                        filename=args.filename)
