import pyodbc as odbc
import igraph as ig
import heapq

class graph_summary:

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

    def get_graph_from_RDFDB(self):
        graph = None
        node_to_supernode = None
        if self.sql_database:
            graph, node_to_supernode = self.get_graph_from_SQLDB()
        else:
            graph, node_to_supernode = self.get_graph_from_file()
        if not self.include_attributes:
            attribute_nodes = graph.vs.select(_degree_gt = 75)
            graph.delete_vertices(attribute_nodes)
        return graph, node_to_supernode


    def get_graph_from_file(self):
        node_to_supernode = {}
        edges = set()
        max_node_id = -1
        count = 0
        with open("out.rdf", "r") as f:
            for line in f:
                arr = line.split(" ")
                subject_name = arr[0]
                predicate_name = arr[1]
                object_name = arr[2]

                if can_skip(subject_name, predicate_name, object_name):
                    continue

                if not node_to_supernode.has_key(subject_name):
                    max_node_id += 1
                    node_to_supernode[subject_name] = max_node_id
                if not node_to_supernode.has_key(object_name):
                    max_node_id += 1
                    node_to_supernode[object_name] = max_node_id
                edges.add((node_to_supernode[subject_name], node_to_supernode[object_name]))
                count += 1
                if count >= 50:
                    break

        g = ig.Graph(directed=self.directed)
        g.add_vertices(range(0, max_node_id + 1))
        g.add_edges(edges)
        return g, node_to_supernode



    def get_graph_from_SQLDB(self):
        cnxn = odbc.connect(r'Driver={SQL Server};Server=.\SQLEXPRESS;Database=' + self.dbname + r';Trusted_Connection=yes;')
        cursor = cnxn.cursor()
        cursor.execute("SELECT * FROM RDF")

        node_to_supernode = {}
        edges = set()
        max_node_id = -1
        count = 0
        while 1:
            count += 1
            row = cursor.fetchone()
            if not row:
                break
            subject_name = row.Subject
            predicate_name = row.Predicate
            object_name = row.Object

            if can_skip(subject_name, predicate_name, object_name):
                continue

            if not node_to_supernode.has_key(subject_name):
                max_node_id += 1
                node_to_supernode[subject_name] = max_node_id
            if not node_to_supernode.has_key(object_name):
                max_node_id += 1
                node_to_supernode[object_name] = max_node_id
            edges.add((node_to_supernode[subject_name], node_to_supernode[object_name]))

        cnxn.close()

        g = ig.Graph(directed=self.directed)
        g.add_vertices(range(0, max_node_id + 1))
        g.add_edges(edges)
        return g, node_to_supernode

    def get_initial_cost(self,node):
        return self.g.vs[node].degree()

    def get_summarization(self):
        if self.g is None:
            return None
        summary, node_to_supernode = self.get_graph_from_RDFDB()
        print "Summary generated"
        for node in range(0,summary.vcount()):
            summary.vs[node]['cost'] = self.get_initial_cost(node)
            summary.vs[node]['contains'] = {node}
        print "Summary annotated"
        #return summary
        h = []
        count = 0
        for u in range(0,summary.vcount()):
            two_hop_neighbors = self.get_two_hop_neighbors(summary, u)

            for v in two_hop_neighbors:
                suv = self.calcSUV(summary,u,v)
                #print suv
                if suv > 0:
                    heapq.heappush(h, (-suv, (u, v)))
            count += 1
            #if count % 10 == 0:
            #print count
            if count % 1000 == 0:
                print count
        i = 0
        while len(h) > 0 and i < 100:
            print h.pop()
        return summary

    def calcSUV(self,summary,u,v):
        cost_u = summary.vs[u]['cost']
        cost_v = summary.vs[v]['cost']
        if cost_u is 0 or cost_v is 0:
            return 0
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

        return float(cost_u + cost_v - cost_w) / float(cost_u + cost_v)


    def get_shared_neighbors(self, graph, u, v):
        if not self.directed:
            neighbors = graph.neighborhood(vertices = [u,v], order = 1, mode = "all")
            return set(neighbors[0]).union(set(neighbors[1]))

    def get_two_hop_neighbors(self,graph,node):
        if not self.directed:
            return graph.neighborhood(vertices = node, order = 2, mode="all")

    def generate_summary(self):
        self.g, self.node_name_to_id = self.get_graph_from_RDFDB()
        print "Graph generated"
        self.s = self.get_summarization()

def can_skip(s,p,o):
    if '#' in s:
        return True
    return False

if __name__ == "__main__":
    #g = graph_summary(False,True,True,False,"out.rdf",False)
    g = graph_summary(False,True,False,False,"LUBMOld")
    print g.s.degree(range(10))
    layout = g.s.layout("kk")
    ig.plot(g.s, layout=layout)

