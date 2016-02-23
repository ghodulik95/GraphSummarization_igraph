import import_graph
import igraph as ig
import random
import time

class Graph_Summary:
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
        graph_importer = import_graph.Graph_importer(self)
        self.g, self.original_id_to_name = graph_importer.get_graph_from_RDFDB()
        del graph_importer

        self.original_id_to_supernode = {}
        for i in range(self.g.vcount()):
            self.original_id_to_supernode[i] = i
        self.s = self.make_blank_summary()
        self.additions = {}
        self.subtractions = {}
        self.max_original_id = self.g.vcount()

        self.generate_summary()
        #self.g = None

    #Returns a copy of self.g with no edges
    def make_blank_summary(self):
        graph = ig.Graph(directed=self.directed)
        graph.add_vertices(self.g.vcount())
        return graph

    #Returns true if the summary has finished generating
    def summary_is_generated(self):
        return self.g is None

    def annotate_summary(self):
        if self.s.ecount() == 0:
            for i in range(0,self.s.vcount()):
                self.s.vs[i]['cost'] = self.get_initial_cost_of_node(i)
                self.s.vs[i]['contains'] = {i}
                self.s.vs[i]['original_id'] = i

    def get_initial_cost_of_node(self,node_index):
        return self.g.vs[node_index].degree()

    def get_node_with_original_id(self, original_id):
        return self.s.vs.select(original_id = original_id)

    def get_vertices_with_original_n_hop_connection(self, super_node,n):
        seed_nodes = super_node['contains']
        original_two_hop_neighbors = set()
        neighborhoods = self.g.neighborhood(vertices=seed_nodes,order=n,mode="all")
        #print neighborhoods
        for neighborhood in neighborhoods:
            for neighbor in neighborhood:
                original_two_hop_neighbors.add(neighbor)
        return self.original_nodes_to_supernodes(original_two_hop_neighbors)

    def original_nodes_to_supernodes(self,original_nodes):
        supernode_original_ids = set(map(lambda x : self.original_id_to_supernode[x], list(original_nodes)))
        super_node_indexes = set()
        for neighbor in self.s.vs.select(original_id_in = supernode_original_ids):
            super_node_indexes.add(neighbor.index)
        super_node_neighbors = set()
        for i in super_node_indexes:
            super_node_neighbors.add(self.s.vs[i])
        return super_node_neighbors

    def get_number_of_connections_between_supernodes(self,u,v):
        return self.get_number_of_connections_in_original(u['contains'], v)

    def get_support_of_edge_between_supernodes(self,u_index,v_index):
        u = self.s.vs[u_index]
        v = self.s.vs[v_index]
        potential = len(u['contains']) * len(v['contains'])
        assert potential != 0
        actual = self.get_number_of_connections_in_original(u['contains'], v)
        return float(actual) / float(potential)

    def get_number_of_connections_in_original(self,original_nodes,neighbor):
        count = 0
        for node in original_nodes:
            for in_neighbor in neighbor['contains']:
                if self.g.are_connected(node, in_neighbor):
                    count += 1
        return count

    def get_potential_number_of_connections_in_original(self,original_nodes,neighbor):
        return len(original_nodes)*len(neighbor['contains'])

    #Calculates s(u,v) of supernodes u and v
    def calc_suv(self,u,v):
        if u['cost'] < 0 or v['cost'] < 0:
            print "NEGATIVE"
        if u['cost'] == 0 or v['cost'] == 0:
            return 0, None

        u_neighbors = self.get_vertices_with_original_n_hop_connection(u,1)
        v_neighbors = self.get_vertices_with_original_n_hop_connection(v,1)

        super_neighbors = u_neighbors.union(v_neighbors)

        #W is u merged with v
        cost_w = 0
        for sn in super_neighbors:
            original_nodes_in_w = u['contains'].union(v['contains'])
            pi_wn = self.get_potential_number_of_connections_in_original(original_nodes_in_w,sn)
            A_wn = self.get_number_of_connections_in_original(original_nodes_in_w,sn)

            if pi_wn < A_wn:
                print "Actual more than potential"

            if pi_wn - A_wn + 1 < A_wn:
                cost_w += pi_wn - A_wn + 1
            else:
                cost_w += A_wn

        return float(u['cost'] + v['cost'] - cost_w) / float(u['cost'] + v['cost']), cost_w

    def pick_random_supernode_in_set(self, s):
        #Two methods :
        # A) Pick a random value in s, find the assosciated supernode, and return that
        #           This method requres linear search across summary. --> expect runtime ~ |Vs| / 2
        # B) Pick a random supernode, return it if it is in s, otherwise keep picking
        #           This method will be much faster unless |s| << |Vs|, in which case it could be very sub-optimal
        #   So, we will attempt B num_attempts_cutoff times. Potentially some analysis can tell us what the optimal cutoff is

        if len(s) > 2:
            num_attempts = 0
            cutoff = self.s.vcount() / 2
            while num_attempts < cutoff:
                rand_index = random.randint(0, self.s.vcount() - 1)
                rand_supernode = self.s.vs[rand_index]
                if rand_supernode['original_id'] in s:
                    return rand_supernode
                num_attempts += 1
        rand_original_id = random.sample(s,1)[0]
        return self.s.vs.find(original_id = rand_original_id)

    def merge_supernodes(self,u,v,cost):
        self.s.add_vertices(1)
        new_index = self.s.vcount() - 1
        new_original_id = self.max_original_id
        self.s.vs[new_index]['cost'] = cost
        self.s.vs[new_index]['contains'] = u['contains'].union(v['contains'])
        self.s.vs[new_index]['original_id'] = new_original_id
        self.max_original_id += 1
        self.update_original_id_to_supernode(u,v,new_original_id)
        self.s.delete_vertices([u,v])
        return new_original_id

    def update_original_id_to_supernode(self,u,v,new_original_id):
        self.assign_new_supernode(u,new_original_id)
        self.assign_new_supernode(v,new_original_id)

    def assign_new_supernode(self,node,new_supernode_original_id):
        for id in node['contains']:
            self.original_id_to_supernode[id] = new_supernode_original_id

    def generate_summary(self):
        self.annotate_summary()
        #print self.s.vs[3489]
        #return
        unfinished = set(self.s.vs['original_id'])
        removed = set()
        print "Beginning"
        start = time.time()
        count = 0
        while len(unfinished) > 0:
            u = self.pick_random_supernode_in_set(unfinished)
            two_hop_neighbors = self.get_vertices_with_original_n_hop_connection(u,2)

            v_best = None
            suv_best = 0
            cost_w_best = None
            for v in two_hop_neighbors:
                if v.index != u.index:
                    suv, cost_w = self.calc_suv(u,v)
                    if suv > suv_best:
                        suv_best = suv
                        v_best = v
                        cost_w_best = cost_w
            #print suv_best
            if suv_best > 0:
                #print u['original_id']
                unfinished.remove(u['original_id'])
                #print v_best['original_id']
                unfinished.remove(v_best['original_id'])
                if u['original_id'] in removed:
                    print "U IN REMOVED"
                if v_best['original_id'] in removed:
                    print "V IN REMOVED"
                removed.add(u['original_id'])
                removed.add(v_best['original_id'])
                new_node_original_id = self.merge_supernodes(u,v_best,cost_w_best)
                unfinished.add(new_node_original_id)
            else:
                unfinished.remove(u['original_id'])
            count += 1
            if count % 50 == 0:
                now = time.time()
                print "%d iterations done, %d seconds elapsed" % (count, (now - start))

        nodes_tried = set()
        for u in self.s.vs:
            nodes_in_u = u['contains']
            potential_neighbors = self.get_vertices_with_original_n_hop_connection(u,1)
            for v in potential_neighbors:
                if v not in nodes_tried:
                    pi_uv = self.get_potential_number_of_connections_in_original(nodes_in_u,v)
                    A_uv = self.get_number_of_connections_in_original(nodes_in_u,v)
                    if A_uv > (pi_uv + 1)/2:
                        self.s.add_edge(u,v)
                        self.add_subtractions(u,v)
                    else:
                        self.add_additions(u,v)
            nodes_tried.add(u)

    def add_subtractions(self,u,v):
        for in_u in u['contains']:
            for in_v in v['contains']:
                if not self.g.are_connected(in_u,in_v):
                    self.add_correction(in_u,in_v,self.subtractions)

    def add_additions(self,u,v):
        for in_u in u['contains']:
            for in_v in v['contains']:
                if self.g.are_connected(in_u,in_v):
                    self.add_correction(in_u,in_v,self.additions)

    def add_correction(self,u,v,correction_dict):
        self.add_correction_with_direction(u,v,correction_dict)
        self.add_correction_with_direction(v,u,correction_dict)

    def add_correction_with_direction(self,u,v,correction_dict):
        if not correction_dict.has_key(u):
            correction_dict[u] = set()
        correction_dict[u].add(v)

if __name__ == "__main__":
    #g = graph_summary_randomized(False,True,False,False,"out.rdf",False)
    g = Graph_Summary(False,True,False,False,"LUBMOld")
    print "Additions: %d" % len(g.additions)
    print "Subtractions: %d" % len(g.subtractions)
    print "Original graph number of vertices: %d" % g.g.vcount()
    print "Summary number of vertics: %d" % g.s.vcount()
    #print g.original_id_to_supernode
    #print g.s.vs['contains']
    #print g.g.summary()
    #layout = g.g.layout("kk")
    #ig.plot(g.g, layout=layout)
    #layout = g.s.layout("kk")
    #ig.plot(g.s, layout=layout)

    num_connected_with_superedge = 0
    num_connected_with_correction = 0
    num_not_connected = 0
    for i in range(3000):
        u_original = random.randint(0,g.g.vcount()-1)
        u_neighborhood = g.g.neighborhood(vertices=u_original,order=1,mode='all')
        u_neighborhood.remove(u_original)
        u_neighbor = random.sample(u_neighborhood, 1)[0]
        #check if these two nodes originally connected are connected in the summary
        super_node_u_original_id = g.original_id_to_supernode[u_original]
        super_node_u = g.s.vs.find(original_id = super_node_u_original_id)
        super_node_v_original_id = g.original_id_to_supernode[u_neighbor]
        super_node_v = g.s.vs.find(original_id= super_node_v_original_id)
        #print super_node_v
        #print super_node_u
        if g.s.are_connected(super_node_u,super_node_v):
            num_connected_with_superedge += 1
        elif g.additions.has_key(u_original) and u_neighbor in g.additions[u_original]:
            num_connected_with_correction += 1
        else:
            print "Nodes not connected: %d %d" % (u_original, u_neighbor)
            num_not_connected += 1

    print "Num connected via super edge: %d" % num_connected_with_superedge
    print "Num connected via correction: %d" % num_connected_with_correction
    print "Num not connected: %d" % num_not_connected

    support = []

    for edge in g.s.es:
        u = edge.source
        v = edge.target
        support.append(g.get_support_of_edge_between_supernodes(u,v))

    print "Average support of super edge: %f" % (sum(support) / float(len(support)))

