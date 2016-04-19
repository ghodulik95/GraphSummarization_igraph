from product import Rational
import gmpy2
import igraph as ig
import random
import math
import numpy

def calc_prob_at_least(v,potential_e,e,i):
    r = Rational()
    for j in range(0,2*i):
        r.multiply_by(e - j)
        r.divide_by(potential_e - j)
    r.multiply_by(gmpy2.comb(v - 2, i))
    return r.value()

def calc_expected_s(num_vertices, num_edges):
    expected_degree = 2.0*num_edges/num_vertices
    possible_num_edges = ((num_vertices - 1)*num_vertices) / 2
    prob_edge = float(num_edges) / possible_num_edges

    i = num_vertices - 2
    prob_exactly_i_shared = {}
    max_i = -1
    first = True
    while i > 0:
        if 2*i <= num_edges:
            prob_at_least_i_shared = calc_prob_at_least(num_vertices,possible_num_edges,num_edges,i)
            if first:
                prob_exactly_i_shared[i] = prob_at_least_i_shared
                max_i = i
                first = False
            else:
                prob_exact = prob_at_least_i_shared
                for j in range(i+1, max_i + 1):
                    prob_exact -= prob_exactly_i_shared[j]
                if prob_exact < 0:
                    prob_exact = 0
                prob_exactly_i_shared[i] = prob_exact
        i -= 1

    expected_num_shared = 0.0
    for i in prob_exactly_i_shared.keys():
        expected_num_shared += i*prob_exactly_i_shared[i]
    #print "Expected number of shared neighbors for %d vertices and %d edges: %f" % (num_vertices, num_edges, expected_num_shared)

    expected_s = (expected_num_shared + prob_edge)/(2*expected_degree)
    return expected_s

def random_graph(num_vertices,num_edges):
    g = ig.Graph(directed=False)
    g.add_vertices(num_vertices)

    edges_added = 0
    while edges_added < num_edges:
        node1 = random.randint(0,num_vertices - 1)
        node2 = random.randint(0,num_vertices - 1)
        if node1 == node2:
            continue
        if g.are_connected(node1, node2):
            continue
        g.add_edge(node1, node2)
        edges_added += 1

    return g

#Calculates s(u,v) of supernodes u and v
def calc_suv(g,u,v):
    u_cost = g.degree(u)
    v_cost = g.degree(v)

    if u_cost == 0 or v_cost == 0:
        return 0

    u_neighbors = set(g.neighborhood(u,2))
    v_neighbors = set(g.neighborhood(v,2))

    neighbors = u_neighbors.union(v_neighbors)

    cost = 0.0
    for n in neighbors:
        pi_wn = 2
        a_wn = 0
        if g.are_connected(n,u):
            a_wn += 1
        if g.are_connected(n,v):
            a_wn += 1

        if pi_wn < a_wn:
            print "Actual more than potential"

        if pi_wn - a_wn + 1 < a_wn:
            cost += pi_wn - a_wn + 1
        else:
            cost += a_wn
    return float(u_cost + v_cost - cost) / float(u_cost + v_cost)

def two_random_nodes(v):
    node1 = random.randint(0,v - 1)
    node2 = random.randint(0,v - 1)
    if node1 == node2:
        return two_random_nodes(v)
    return node1, node2

def calc_avg_s(v,e):
    suvs = []
    for i in range(0,v,v/100 + 1):
        g = random_graph(v,e)
        for j in range(0,v):
            n1,n2 = two_random_nodes(v)
            suvs.append(calc_suv(g,n1,n2))
            """u = random.randint(0,v-1)
            neighbors = get_2hop_neighbors(g,u)
            for s in neighbors:
                suv = calc_suv(g,s,u)
                suvs.append(suv)"""
    suvs = numpy.array(suvs)
    return numpy.mean(suvs), numpy.std(suvs)

def get_2hop_neighbors(g,n):
    neighbors = g.neighborhood(n,1)
    neighbors.remove(n)
    two_hop = set()
    for neighbor in neighbors:
        ns = g.neighborhood(neighbor,1)
        ns.remove(neighbor)
        ns.remove(n)
        for two_n in ns:
            two_hop.add(two_n)
    return two_hop

def calc_avg_s_scalefree(v,e):
    suvs = []
    for i in range(int(math.ceil(math.sqrt(v)))):
        graph = generate_scale_free(v,e)
        for j in range(int(math.ceil(math.sqrt(v)))):
            node1,node2 = two_random_nodes(v)
            neighbors = get_2hop_neighbors(graph, node1)
            best_suv = 0
            for n in neighbors:
                if n != node1:
                    suv = calc_suv(graph,node1,n)
                    if suv > best_suv:
                        best_suv = suv
            suvs.append(best_suv)
    suvs = numpy.array(suvs)
    return numpy.mean(suvs), numpy.std(suvs)

def generate_scale_free(v,e):
    return ig.GraphBase.Static_Power_Law(v,e,2,loops=True)

if __name__ == "__main__":
    f = open("resultsScalefreeLarger.csv", "w")
    f.write('"Num Edges","Num Vertices","Avg","Std"\n')
    for v in range(1000,10000, 1500):
        for e in range(2*v, ((v-1)*v/2)*95/100, (((v-1)*v/2)*95/100-2*v)/15):
            print "Graph with E=%d, V=%d" % (e,v)
            avg,std = calc_avg_s_scalefree(v,e)
            print "Avg reduced cost: %f, Standard Deviation: %f" % (avg,std)
            f.write("%d,%d,%f,%f\n" % (e,v,avg,std))
            f.flush()
        f.flush()
    f.close()