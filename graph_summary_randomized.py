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

    def get_summarization(self, graph_importer):
        if self.g is None:
            return None
        summary, _ = graph_importer.get_graph_from_RDFDB()
        unfinished = set(i for i in range(summary.vcount()))
        next_new_id = summary.vcount()
        finished = set()

        print "Summary generated"
        for node in range(0,summary.vcount()):
            summary.vs[node]['cost'] = self.get_initial_cost(node)
            summary.vs[node]['contains'] = {node}
            summary.vs[node]['original_id'] = node
        print "Summary annotated"
        count = 0

        #import pdb
        #pdb.set_trace()
        while len(unfinished) > 0:
            u_original_id = random.sample(unfinished, 1)[0]
            u = summary.vs.select(original_id = u_original_id)[0].index
            two_hop_neighbors = self.get_two_hop_neighbors(summary, u)
            v_best = None
            suv_best = float('-inf')
            cost_w_best = None
            for v in two_hop_neighbors:
                suv, cost_w = self.calcSUV(summary, u, v)
                if suv > suv_best:
                    v_best = v
                    suv_best = suv
                    cost_w_best = cost_w
            if suv_best > 0:
                summary.add_vertices(1)
                summary.vs[summary.vcount() - 1]['original_id'] = next_new_id
                summary.vs[summary.vcount() - 1]['contains'] = summary.vs[u]['contains'].union(summary.vs[v]['contains'])
                summary.vs[summary.vcount() - 1]['cost'] = cost_w_best
                v_original_id = summary.vs[v_best]['original_id']
                if u_original_id in unfinished:
                    unfinished.remove(u_original_id)
                if v_original_id in unfinished:
                    unfinished.remove(v_original_id)
                unfinished.add(next_new_id)
                summary.delete_vertices([u,v])
                next_new_id += 1
            else:
                unfinished.remove(u_original_id)
                finished.add(u_original_id)
            count += 1
            if count % 100 == 0:
                print count

        return summary

    def calcSUV(self,summary,u,v):
        cost_u = summary.vs[u]['cost']
        cost_v = summary.vs[v]['cost']
        if cost_u is 0 or cost_v is 0:
            return 0, None
        cost_w = 0
        num_nodes_in_w = len(summary.vs[u]['contains']) + len(summary.vs[v]['contains'])
        super_neighbors = self.get_shared_neighbors(summary, u, v)

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


    def get_shared_neighbors(self, graph, u, v):
        if not self.directed:
            neighbors = graph.neighborhood(vertices = [u,v], order = 1, mode = "all")
            return set(neighbors[0]).union(set(neighbors[1]))

    def get_two_hop_neighbors(self,graph,node):
        if not self.directed:
            return graph.neighborhood(vertices = node, order = 2, mode="all")

    def generate_summary(self):
        graph_importer = Graph_importer(self)
        self.g, self.id_to_node_name = graph_importer.get_graph_from_RDFDB()
        print "Graph generated"
        self.s = self.get_summarization(graph_importer)

def can_skip(s,p,o):
    if '#' in s:
        return True
    return False

if __name__ == "__main__":
    #g = graph_summary(False,True,True,False,"out.rdf",False)
    g = graph_summary_randomized(False,True,False,False,"LUBMOld")
    print g.s.degree(range(10))
    layout = g.s.layout("kk")
    ig.plot(g.s, layout=layout)

