from import_graph import Graph_importer
import igraph as ig
import random

class graph_summary_randomized:

    def __init__(self, directed, include_edges, include_attributes, edges_annotated, dbname, sql_database = True, wa=1, wc = 1, we = 1 ):
        self.directed = directed
        self.include_edges = include_edges
        self.include_attributes = include_attributes
        self.edges_annotated = edges_annotated
        self.wa = wa
        self.wc = wc
        self.we = we
        self.dbname = dbname
        self.sql_database = sql_database
        self.generate_summary()

    def get_initial_cost(self,node):
        return self.g.vs[node].degree()

    def get_summarization(self):
        if self.g is None:
            return None
        summary = ig.Graph(directed=self.directed)
        summary.add_vertices(self.g.vcount())

        print "Summary generated"
        node_to_original_id_supernode = {}
        for node in range(0,summary.vcount()):
            summary.vs[node]['cost'] = self.get_initial_cost(node)
            summary.vs[node]['contains'] = set([node])
            summary.vs[node]['original_id'] = node
            node_to_original_id_supernode[node] = node
        unfinished = set(summary.vs['original_id'])
        next_new_id = summary.vcount()
        finished = set()
        print "Summary annotated"
        count = 0

        #import pdb
        #pdb.set_trace()
        while len(unfinished) > 0:
            u_original_id = random.sample(unfinished, 1)[0]
            u = summary.vs.find(original_id = u_original_id)
            u = u.index
            two_hop_neighbors = self.get_two_hop_neighbors(summary, u, node_to_original_id_supernode)
            v_best = None
            suv_best = 0
            cost_w_best = None
            for v_index in two_hop_neighbors:
                if v_index == u:
                    continue
                suv, cost_w = self.calcSUV(summary, u, v_index, node_to_original_id_supernode)
                if suv > suv_best:
                    v_best = v_index
                    suv_best = suv
                    cost_w_best = cost_w
            if suv_best > 0:
                print "MERGE: "+str(len(unfinished))
                summary.add_vertices(1)
                summary.vs[summary.vcount() - 1]['original_id'] = next_new_id
                contains_nodes = summary.vs[u]['contains'].union(summary.vs[v_index]['contains'])
                summary.vs[summary.vcount() - 1]['contains'] = contains_nodes
                summary.vs[summary.vcount() - 1]['cost'] = cost_w_best
                v_original_id = summary.vs[v_best]['original_id']
                if u_original_id in unfinished:
                    unfinished.remove(u_original_id)
                if v_original_id in unfinished:
                    unfinished.remove(v_original_id)
                unfinished.add(next_new_id)
                summary.delete_vertices([u,v_best])
                self.update_node_to_supernode(node_to_original_id_supernode, contains_nodes, next_new_id)
                next_new_id += 1
            else:
                unfinished.remove(u_original_id)
                finished.add(u_original_id)
            count += 1
            if count % 10 == 0:
                print len(unfinished)
        additions = subtractions = set()
        for u in summary.vs:
            u_index = u.index
            potential_neighbors = self.get_potential_neighbors(summary,u)
            for v_index in potential_neighbors:
                A_uv = self.calc_num_connections_in_original_graph(summary,u_index,v_index)
                pi_uv = len(summary.vs[u_index]['contains']) * len(summary.vs[v_index]['contains'])
                #print u['contains']
                #print str(A_uv)+" "+str(pi_uv)
                if A_uv > (pi_uv + 1)/2:
                    summary.add_edge(u,v_index)

        return summary, additions, subtractions

    def update_node_to_supernode(self,node_to_original_id_supernode, contains_nodes, next_new_id):
        for n in contains_nodes:
            node_to_original_id_supernode[n] = next_new_id

    def get_potential_neighbors(self,summary,node):
        potential_neighbors = set()
        for n in node['contains']:
            neighbors = self.g.neighborhood(vertices=n,order=1,mode="all")
            for neighbor in neighbors:
                potential_neighbors.add(neighbor)
        return potential_neighbors

    def calc_num_connections_in_original_graph(self,summary,u,v):
        A_wn = 0
        for u_contains in summary.vs[u]['contains']:
            for v_contains in summary.vs[v]['contains']:
                if self.g.are_connected(u_contains,v_contains):
                    A_wn += 1
        return A_wn

    def calcSUV(self,summary,u,v, node_to_supernode):
        cost_u = summary.vs[u]['cost']
        cost_v = summary.vs[v]['cost']
        if cost_u is 0 or cost_v is 0:
            return 0, None
        cost_w = 0
        num_nodes_in_w = len(summary.vs[u]['contains']) + len(summary.vs[v]['contains'])
        super_neighbors = self.get_shared_neighbors(summary, u, v, node_to_supernode)

        for super_n in super_neighbors:
            A_wn = 0
            for n in summary.vs[super_n]['contains']:
                for u_node in summary.vs[u]['contains']:
                    if self.g.are_connected(n,u_node):
                        A_wn += 1
            pi_wn = num_nodes_in_w * len(summary.vs[super_n]['contains'])
            if pi_wn - A_wn + 1 < A_wn:
                cost_w += pi_wn - A_wn + 1
            else:
                cost_w += A_wn

        return float(cost_u + cost_v - cost_w) / float(cost_u + cost_v), cost_w


    def get_shared_neighbors(self, summary, u, v, node_to_supernode):
        if not self.directed:
            neighborhoods = self.g.neighborhood(vertices = summary.vs[u]['contains'].union(summary.vs[v]['contains']), order = 1, mode = "all")
            shared_neighbors = []
            for neighborhood in neighborhoods:
                for n in neighborhood:
                    shared_neighbors.append(node_to_supernode[n])
                    print node_to_supernode[n]

            return set(map(lambda x: summary.vs.find(original_id=x).index, shared_neighbors))

    def get_two_hop_neighbors(self,summary,node, node_to_supernode):
        if not self.directed:
            two_hop_neighbors = []
            neighborhoods = self.g.neighborhood(vertices = summary.vs[node]['contains'], order = 2, mode="all")
            for neighborhood in neighborhoods:
                for n in neighborhood:
                    two_hop_neighbors.append(n)

            return set(map(lambda x: summary.vs.find(original_id=node_to_supernode[x]).index, two_hop_neighbors))
        return None

    def generate_summary(self):
        graph_importer = Graph_importer(self)
        self.g, self.id_to_node_name = graph_importer.get_graph_from_RDFDB()
        print "Graph generated"
        self.s, self.additions, self.subtractions = self.get_summarization()

def can_skip(s,p,o):
    if '#' in s:
        return True
    return False

if __name__ == "__main__":
    #g = graph_summary_randomized(False,True,False,False,"out.rdf",False)
    g = graph_summary_randomized(False,True,False,False,"LUBMOld")
    print g.s.vcount()
    print g.g.vcount()
    layout = g.s.layout("kk")
    ig.plot(g.s, layout=layout)

