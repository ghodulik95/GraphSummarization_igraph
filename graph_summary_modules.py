import import_graph
import igraph as ig
import random
import time
import unique_colors
import math

class Graph_Summary_Module:
    def __init__(self, directed=None, include_edges=None, include_attributes=None, edges_annotated=None, dbname=None, sql_database = True, source_graph=None,original_id_to_node_name=None, source_summary=None ):
        self.cutoff = None
        self.display_req = None
        self.display_comp = None
        self.step=None
        self.num_allowable_skips=None
        if source_summary is None:
            self.source_summary = None
            self.directed = directed
            self.include_edges = include_edges
            self.include_attributes = include_attributes
            self.edges_annotated = edges_annotated
            self.dbname = dbname
            self.sql_database = sql_database
            if source_graph is None:
                graph_importer = import_graph.Graph_importer(self)
                self.g, self.original_id_to_name = graph_importer.get_graph_from_RDFDB()
                del graph_importer

                self.original_id_to_supernode_name = {}
            else:
                self.g = source_graph.copy()
                self.original_id_to_name = original_id_to_node_name.copy()

            self.original_id_to_supernode_name = {}
            self.s = self.make_blank_summary()
            self.additions = {}
            self.subtractions = {}
            self.max_original_id = self.g.vcount()
            self.annotate_summary()
            self.generate_summary()
            #self.g = None
        else:
            self.source_summary = source_summary # type: Graph_Summary
            self.directed = source_summary.directed
            self.g = Graph_Summary_Module.trim(self.source_summary.s.as_undirected()) # type : ig.Graph
            self.original_id_to_supernode_name = {}
            self.s = self.make_blank_summary()
            self.additions = {}
            self.subtractions = {}
            self.max_original_id = self.g.vcount()
            self.annotate_summary()
            self.s.vs['haircontains'] = [None for _ in range(self.s.vcount())]
            self.generate_summary()

    @staticmethod
    def trim(g):
        """
        :type g: ig.Graph
        """
        degree_1_nodes = g.vs.select(_degree = 1)
        if len(degree_1_nodes) == 0:
            return g
        neighbors = g.neighborhood(vertices=degree_1_nodes,order=1)
        for i in range(len(degree_1_nodes)):
            hair = degree_1_nodes[i]
            parent = g.vs[neighbors[i]]
            parent['hairname'] = hair['name']
            parent['haircontains'] = hair['contains']
        g.delete_vertices(degree_1_nodes)
        return g

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
                self.s.vs[i]['contains'] = set([i])
                self.s.vs[i]['name'] = self.get_name_form(i)
                self.s.vs[i]['iteration'] = 0
                self.original_id_to_supernode_name[i] = self.get_name_form(i)

    def get_name_form(self,i):
        return "Node "+str(i)

    def get_initial_cost_of_node(self,node_index):
        return self.g.vs[node_index].degree()

    def get_node_with_original_name(self, original_name):
        return self.s.vs.find(original_name)

    def get_node_with_original_node_index(self, original_index):
        return self.get_node_with_original_name(self.get_name_form(original_index))

    def get_vertices_with_original_two_hop_connection_exactly(self, super_node):
        seed_nodes = list(super_node['contains'])
        original_two_hop_neighbors = set()
        neighbors = set()
        neighborhoods = self.g.neighborhood(vertices=seed_nodes,order=1,mode="all")
        #print neighborhoods
        for i in range(len(neighborhoods)):
            for neighbor in neighborhoods[i]:
                if seed_nodes[i] != neighbor:
                    neighbors.add(neighbor)
        seed_nodes = list(neighbors)
        neighborhoods = self.g.neighborhood(vertices=seed_nodes,order=1,mode="all")
        for i in range(len(neighborhoods)):
            for neighbor in neighborhoods[i]:
                if seed_nodes[i] != neighbor:
                    original_two_hop_neighbors.add(neighbor)
        return self.original_nodes_to_supernodes(original_two_hop_neighbors)


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
        supernode_names = set(map(lambda x : self.original_id_to_supernode_name[x], list(original_nodes)))
        super_node_indexes = set()
        for neighbor in self.s.vs.select(name_in = supernode_names):
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

    def get_cost_of_supernode(self,node):
        neighbors = self.get_vertices_with_original_n_hop_connection(node,1)
        return self.get_cost_of_supernode_containing(node['contains'], neighbors)

    def get_cost_of_supernode_containing(self,nodes, super_neighbors):
        cost = 0
        for sn in super_neighbors:
            pi_wn = self.get_potential_number_of_connections_in_original(nodes,sn)
            a_wn = self.get_number_of_connections_in_original(nodes,sn)

            if pi_wn < a_wn:
                print "Actual more than potential"

            if pi_wn - a_wn + 1 <= a_wn:
                cost += pi_wn - a_wn + 1
            else:
                cost += a_wn
        return cost

    #Calculates s(u,v) of supernodes u and v
    def calc_suv(self,u,v):
        u_cost = self.get_cost_of_supernode(u)
        v_cost = self.get_cost_of_supernode(v)
        if u_cost < 0 or v_cost < 0:
            print "NEGATIVE"
        if u_cost == 0 or v_cost == 0:
            return 0, None

        u_neighbors = self.get_vertices_with_original_n_hop_connection(u,1)
        v_neighbors = self.get_vertices_with_original_n_hop_connection(v,1)

        super_neighbors = u_neighbors.union(v_neighbors)
        original_nodes_in_w = u['contains'].union(v['contains'])

        cost_w = self.get_cost_of_supernode_containing(original_nodes_in_w, super_neighbors)

        return float(u_cost + v_cost - cost_w) / float(u_cost + v_cost), cost_w

    def pick_random_supernode_in_set(self, s):
        #Two methods :
        # A) Pick a random value in s, find the assosciated supernode, and return that
        #           This method requres linear search across summary. --> expect runtime ~ |Vs| / 2
        # B) Pick a random supernode, return it if it is in s, otherwise keep picking
        #           This method will be much faster unless |s| << |Vs|, in which case it could be very sub-optimal
        #   So, we will attempt B num_attempts_cutoff times. Potentially some analysis can tell us what the optimal cutoff is
        """
        if len(s) > 2:
            num_attempts = 0
            cutoff = self.s.vcount() / 2
            while num_attempts < cutoff:
                rand_index = random.randint(0, self.s.vcount() - 1)
                rand_supernode = self.s.vs[rand_index]
                if rand_supernode['name'] in s:
                    return rand_supernode
                num_attempts += 1"""
        rand_original_name = random.sample(s,1)[0]
        return self.s.vs.find(rand_original_name)

    def merge_supernodes(self,u,v,cost):
        self.s.add_vertices(1)
        new_index = self.s.vcount() - 1
        new_name = self.get_name_form(self.max_original_id)
        self.s.vs[new_index]['cost'] = cost
        self.s.vs[new_index]['contains'] = u['contains'].union(v['contains'])
        self.s.vs[new_index]['name'] = new_name
        self.max_original_id += 1
        self.update_original_id_to_supernode(u,v,new_name)
        self.s.delete_vertices([u,v])
        return new_name

    def update_original_id_to_supernode(self, u, v, new_name):
        self.assign_new_supernode(u, new_name)
        self.assign_new_supernode(v, new_name)

    def assign_new_supernode(self, node, new_name):
        for id in node['contains']:
            self.original_id_to_supernode_name[id] = new_name

    def generate_summary(self):
        start = time.time()
        neighbors = {}
        for n in self.s.vs:
            n_neighbors = self.g.neighborhood(vertices=n, order=1)
            n_neighbors_tuple = tuple(sorted(n_neighbors))
            if not neighbors.has_key(n_neighbors_tuple):
                neighbors[n_neighbors_tuple] = []
            neighbors[n_neighbors_tuple].append(n['name'])

            n_neighbors = filter(lambda x: n.index != x, n_neighbors)
            n_neighbors_tuple = tuple(sorted(n_neighbors))
            if not neighbors.has_key(n_neighbors_tuple):
                neighbors[n_neighbors_tuple] = []
            neighbors[n_neighbors_tuple].append(n['name'])


        to_merge = [neighbors[x] for x in filter(lambda l : len(neighbors[l]) > 1, neighbors.keys())]
        already_merged = set()
        iteration = 0
        for nodes_to_merge in to_merge:
            nodes = list(set(nodes_to_merge).difference(already_merged))
            u = self.s.vs(name = nodes[0])[0]
            v = None
            for i in range(1,len(nodes)):
                v = self.s.vs(name = nodes[i])[0]
                new_name = self.merge_supernodes(u,v,1)
                u = self.s.vs(name = new_name)[0]
                iteration += 1
            u['iteration'] = iteration
            already_merged.update(nodes)

        self.put_edges_on_summary()
        now = time.time()
        self.runtime = (now - start)
        self.make_drawable()

    def put_edges_on_summary(self,req=0.5,comp="gr"):
        nodes_tried = set()
        self.additions.clear()
        self.subtractions.clear()
        self.s.delete_edges(self.s.es)
        for u in self.s.vs:
            nodes_in_u = u['contains']
            potential_neighbors = self.get_vertices_with_original_n_hop_connection(u,1)
            for v in potential_neighbors:
                if v not in nodes_tried:
                    pi_uv = self.get_potential_number_of_connections_in_original(nodes_in_u,v)
                    A_uv = self.get_number_of_connections_in_original(nodes_in_u,v)
                    if (float(A_uv)/pi_uv > req and comp == "gr") or (float(A_uv)/pi_uv >= req and comp == "gre") :
                        self.s.add_edge(u,v)
                        self.add_subtractions(u,v)
                    else:
                        self.add_additions(u,v)
            nodes_tried.add(u)

    def get_cost(self):
        return self.s.ecount() + len(self.additions) + len(self.subtractions)

    def make_drawable(self):
        colors = unique_colors.uniquecolors(self.s.vcount()*2 + 2)
        for n in self.s.vs:
            if self.source_summary is None:
                n['size'] = 30 + math.log(len(n['contains']),2)*7
            else:
                hairsize = 0
                for c in n['contains']:
                    hairsize += len(self.g.vs[c]['haircontains']) if self.g.vs[c]['haircontains'] is not None else 0
                n['size'] = 30 + math.log(len(n['contains'])+hairsize,2)*7
            n['label'] = "%d,%d" % (n['iteration'],len(n['contains']))
            color = colors.pop()
            n['color'] = color
            for c in n['contains']:
                self.g.vs[c]['color'] = color
                self.g.vs[c]['label'] = "%d,%d" % (c,(n['iteration']))
                if self.source_summary is None:
                    self.g.vs[c]['size'] = 30
        for e in self.s.es:
            e['width'] = 5*self.get_support_of_edge_between_supernodes(e.source, e.target)
            e['label'] = self.get_support_of_edge_between_supernodes(e.source, e.target)

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

def visualize(filename, g):
    layout = g.g.layout("kk")
    visual_style = {}
    visual_style["layout"] = layout
    visual_style["bbox"] = (1000, 1000)
    #visual_style["margin"] = 10
    ig.plot(g.g, **visual_style).save(filename+"_original.png")
    layout = g.s.layout()
    visual_style = {}
    visual_style["layout"] = layout
    visual_style["bbox"] = (1000, 1000)
    #visual_style["margin"] = 10
    ig.plot(g.s, **visual_style).save(filename+"_summary.png")

def write_report(filename, g):
    f = open(filename+".txt", "w")
    f.write("Additions: %d\n" % len(g.additions))
    f.write("Subtractions: %d\n" % len(g.subtractions))
    f.write("Original graph number of vertices: %d\n" % g.g.vcount())
    f.write("Summary number of vertices: %d\n" % g.s.vcount())
    f.write("Original graph number of edges: %d\n" % g.g.ecount())
    f.write("Summary number of superedges: %d\n" % g.s.ecount())
    f.write("Summary cost: %d\n" % g.get_cost())

    #f.write(g.original_id_to_supernode
    #f.write(g.s.vs['contains']
    #f.write(g.g.summary()

    num_connected_with_superedge = 0
    num_connected_with_correction = 0
    num_not_connected = 0
    for i in range(3000):
        u_original = random.randint(0,g.g.vcount()-1)
        u_neighborhood = g.g.neighborhood(vertices=u_original,order=1,mode='all')
        u_neighborhood.remove(u_original)
        if len(u_neighborhood) == 0:
            continue
        u_neighbor = random.sample(u_neighborhood, 1)[0]
        #check if these two nodes originally connected are connected in the summary
        super_node_u_name = g.original_id_to_supernode_name[u_original]
        super_node_u = g.s.vs.find(super_node_u_name)
        super_node_v_name = g.original_id_to_supernode_name[u_neighbor]
        super_node_v = g.s.vs.find(super_node_v_name)
        #f.write(super_node_v
        #f.write(super_node_u
        if g.s.are_connected(super_node_u,super_node_v):
            num_connected_with_superedge += 1
        elif g.additions.has_key(u_original) and u_neighbor in g.additions[u_original]:
            num_connected_with_correction += 1
        else:
            f.write("Nodes not connected: %d %d\n" % (u_original, u_neighbor))
            num_not_connected += 1

    f.write("Num connected via super edge: %d\n" % num_connected_with_superedge)
    f.write("Num connected via correction: %d\n" % num_connected_with_correction)
    f.write("Num not connected: %d\n" % num_not_connected)

    support = []

    for edge in g.s.es:
        u = edge.source
        v = edge.target
        support.append(g.get_support_of_edge_between_supernodes(u,v))

    f.write("Average support of super edge: %f\n" % (sum(support) / float(len(support))))

    for v in g.s.vs:
        f.write("%s contains nodes \n" % v['label'])
        for n in v['contains']:
            if g.source_summary is None:
                f.write(g.original_id_to_name[n]+"\n")
            else:
                original_contains = g.source_summary.s.vs[n]['contains']
                for o in original_contains:
                    f.write(g.source_summary.original_id_to_name[n]+"\n")


    f.write("Additions:\n")
    for k,v in g.additions.items():
        for c in v:
            f.write("+ (%d,%d)\n" % (k,c))

    f.write("Subtractions:\n")
    for k,v in g.subtractions.items():
        for c in v:
            f.write("- (%d,%d)\n" % (k,c))

    f.close()

if __name__ == "__main__":
    dbname = "DBLP4"
    #g = graph_summary_randomized(False,True,False,False,"out.rdf",False)
    g = Graph_Summary(False,True,False,False,dbname)

    g2 = Graph_Summary(source_summary=g)

    visualize("DBLP50_modules",g)
    #write_report("DBLP50_modules",g)

    visualize("DBLP50_modulesthird",g3)
    #write_report("DBLP50_modulessecond",g2)

    print g.get_cost()
    """
    layout = g.g.layout("kk")
    visual_style = {}
    visual_style["layout"] = layout
    visual_style["bbox"] = (1100, 1100)
    #visual_style["margin"] = 10
    ig.plot(g.g, **visual_style).save("DBLP300_original.png")
    layout = g.s.layout()
    visual_style = {}
    visual_style["layout"] = layout
    visual_style["bbox"] = (1100, 1100)
    #visual_style["margin"] = 10
    ig.plot(g.s, **visual_style).save("DBLP300_firstSummary.png")

    layout = g2.g.layout("kk")
    visual_style = {}
    visual_style["layout"] = layout
    visual_style["bbox"] = (1650, 1650)
    #visual_style["margin"] = 10
    ig.plot(g2.g, **visual_style).save("DBLP300_firstSummaryNo1degree.png")
    layout = g2.s.layout()
    visual_style = {}
    visual_style["layout"] = layout
    visual_style["bbox"] = (1650, 1650)
    #visual_style["margin"] = 10
    ig.plot(g2.s, **visual_style).save("DBLP300_secondsummary.png")
    """

