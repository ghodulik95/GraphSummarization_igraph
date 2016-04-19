import import_graph
import igraph as ig
import random
import time
import unique_colors
import math

class Graph_Summary:
    def __init__(self, directed=None, include_edges=None, include_attributes=None, edges_annotated=None, dbname=None, sql_database = True, wa=1, wc = 1, we = 1, source_summary=None ):
        if source_summary is None:
            self.source_summary = None
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
            self.g = Graph_Summary.trim(self.source_summary.s.as_undirected()) # type : ig.Graph
            self.original_id_to_supernode_name = {}
            self.s = self.make_blank_summary()
            self.additions = {}
            self.subtractions = {}
            self.max_original_id = self.g.vcount()
            self.annotate_summary()
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
                self.s.vs[i]['contains'] = {i}
                self.s.vs[i]['name'] = self.get_name_form(i)
                self.s.vs[i]['iteration'] = i
                self.original_id_to_supernode_name[i] = self.get_name_form(i)

    def get_name_form(self,i):
        return "Node "+str(i)

    def get_node_with_original_name(self, original_name):
        return self.s.vs.find(original_name)

    def get_node_with_original_node_index(self, original_index):
        return self.get_node_with_original_name(self.get_name_form(original_index))

    def get_vertices_with_original_two_hop_connection_exactly(self, node):
        original_two_hop_neighbors = set()
        neighbors = set()
        neighborhood = self.g.neighbors(node)
        for neighbor in neighborhood:
            if node != neighbor:
                neighbors.add(neighbor)
        seed_nodes = list(neighbors)
        neighborhoods = self.g.neighborhood(vertices=seed_nodes,order=1,mode="all")
        for i in range(len(neighborhoods)):
            for neighbor in neighborhoods[i]:
                if seed_nodes[i] != neighbor and node != neighbor:
                    original_two_hop_neighbors.add(neighbor)
        return original_two_hop_neighbors


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

    def pick_random_node_from_set(self, s):
        rand_original_name = random.sample(s,1)[0]
        return rand_original_name

    def get_summary_indexes(self,original_indexes):
        summary_indexes = set()
        for id in original_indexes:
            name = self.original_id_to_supernode_name[id]
            index = self.s.vs.find(name).index
            summary_indexes.add(index)
        return summary_indexes

    def merge_supernodes(self,to_merge_original_ids):
        self.s.add_vertices(1)
        new_index = self.s.vcount() - 1
        new_name = self.get_name_form(self.max_original_id)
        self.s.vs[new_index]['contains'] = to_merge_original_ids
        self.s.vs[new_index]['name'] = new_name
        #self.s.vs[new_index]['iteration'] = 1
        self.max_original_id += 1
        summary_ids = self.get_summary_indexes(to_merge_original_ids)
        self.update_original_id_to_supernode(to_merge_original_ids,new_name)
        self.s.delete_vertices(summary_ids)
        return new_name

    def update_original_id_to_supernode(self, to_merge_original_ids, new_name):
        for id in to_merge_original_ids:
            self.assign_new_supernode(id, new_name)

    def assign_new_supernode(self, id, new_name):
        self.original_id_to_supernode_name[id] = new_name

    def get_dense_subgraph_nodes(self,u):
        two_hop_neighbors = self.get_vertices_with_original_two_hop_connection_exactly(u)
        u_neighbors = set(self.g.neighbors(u))
        to_merge = set([u])
        for n in two_hop_neighbors:
            n_neighbors = set(self.g.neighbors(n))
            common_neighbors =  u_neighbors.intersection(n_neighbors)
            all_neighbors = u_neighbors.union(n_neighbors)
            uncommon_neighbors = all_neighbors.difference(common_neighbors)
            percent_common = float(len(common_neighbors)) / len(all_neighbors)
            percent_uncommon = float(len(uncommon_neighbors)) / len(all_neighbors)
            if percent_common > percent_uncommon:
                to_merge.add(n)
        return to_merge

    def generate_summary(self):
        #self.annotate_summary()
        #print self.s.vs[3489]
        #return
        v = self.g.vcount()
        e = self.g.ecount()

        unvisited = set([i for i in range(v)])
        visited = set()

        start = time.time()
        count = v
        while len(unvisited) > 0:

            u = self.pick_random_node_from_set(unvisited)

            dense_subgraph_nodes = self.get_dense_subgraph_nodes(u)
            dense_subgraph_nodes.difference_update(visited)
            if len(dense_subgraph_nodes) > 1:
                #print "U: %d" % u
                #print dense_subgraph_nodes
                new_name = self.merge_supernodes(dense_subgraph_nodes)
                self.s.vs.find(new_name)['iteration'] = count
            count+=1
            unvisited.difference_update(dense_subgraph_nodes)
            visited.update(dense_subgraph_nodes)

        nodes_tried = set()
        for u in self.s.vs:
            nodes_in_u = u['contains']
            potential_neighbors = self.get_vertices_with_original_n_hop_connection(u,1)
            for v in potential_neighbors:
                if v not in nodes_tried:
                    pi_uv = self.get_potential_number_of_connections_in_original(nodes_in_u,v)
                    A_uv = self.get_number_of_connections_in_original(nodes_in_u,v)
                    if float(A_uv)/pi_uv > 0.5:# int(math.floor((pi_uv + 1)/2.0)):
                        self.s.add_edge(u,v)
                        self.add_subtractions(u,v)
                    else:
                        self.add_additions(u,v)
            nodes_tried.add(u)
        self.make_drawable()
        now = time.time()
        self.runtime = (now - start)

    def get_cost(self):
        return self.s.ecount() + len(self.additions) + len(self.subtractions)

    def make_drawable(self):
        colors = unique_colors.uniquecolors(self.s.vcount()*2 + 2)
        for n in self.s.vs:
            n['size'] = 30 + math.log(len(n['contains']),2)*7
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
    f.write("%s - %d" % (dbname, g.runtime))
    f.write("Additions: %d\n" % len(g.additions))
    f.write("Subtractions: %d\n" % len(g.subtractions))
    f.write("Original graph number of vertices: %d\n" % g.g.vcount())
    f.write("Summary number of vertices: %d\n" % g.s.vcount())
    f.write("Original graph number of edges: %d\n" % g.g.ecount())
    f.write("Summary number of superedges: %d\n" % g.s.ecount())
    f.write("Summary cost: %d\n" % g.get_cost())
    f.write("Cutoff: %f\n" % g.cutoff)

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
    print "First done"
    #g2 = Graph_Summary(source_summary=g)

    visualize("DBLP300_dense_subgraphs",g)
    write_report("DBLP300_dense_subgraphs",g)
    #visualize("DBLP300_testingsecond",g2)
    #write_report("DBLP300_testingsecond",g2)

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

