import pyodbc as odbc
import igraph as ig
import random

class Graph_importer:

    def __init__(self, graph_summary_specs=None, dbname = None, num_vertices = None, num_edges = None):
        if graph_summary_specs is not None:
            self.directed = graph_summary_specs.directed
            self.include_edges = graph_summary_specs.include_edges
            self.include_attributes = graph_summary_specs.include_attributes
            self.edges_annotated = graph_summary_specs.edges_annotated
            self.dbname = graph_summary_specs.dbname
            self.sql_database = graph_summary_specs.sql_database
        else:
            self.directed = False
            self.include_edges = True
            self.include_attributes = False
            self.edges_annotated = False
            self.dbname = dbname if dbname is not None else "DBLP4"
            self.sql_database = True

        self.num_vertices = num_vertices
        self.num_edges = num_edges

    def get_graph_from_RDFDB(self,cutoff=None,year_start=None,year_end=None):
        graph = None
        id_to_node_name = None
        if self.dbname == "random":
            return self.get_random_graph()
        if self.sql_database:
            if cutoff is None:
                graph, id_to_node_name = self.get_graph_from_SQLDB()
            else:
                graph, id_to_node_name = self.get_graph_from_SQLDB(cutoff,year_s=year_start,year_e=year_end)
        else:
            graph, id_to_node_name = self.get_graph_from_file()

        if not self.include_attributes:
            attribute_nodes = graph.vs.select(_degree_gt = 5000)
            graph.delete_vertices(attribute_nodes)
        return graph, id_to_node_name

    def get_random_graph(self):
        g = ig.Graph()
        g.add_vertices(self.num_vertices)

        edges_added = 0
        while edges_added < self.num_edges:
            node1 = random.randint(0,self.num_vertices - 1)
            node2 = random.randint(0,self.num_vertices - 1)
            if node1 == node2:
                continue
            if g.are_connected(node1, node2):
                continue
            g.add_edge(node1, node2)
            edges_added += 1
        id_to_node_name = {i:str(i) for i in range(0,self.num_vertices)}

        return g, id_to_node_name

    def get_graph_from_file(self):
        node_name_to_id = {}
        id_to_node_name = {}
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

                if not node_name_to_id.has_key(subject_name):
                    max_node_id += 1
                    node_name_to_id[subject_name] = max_node_id
                    id_to_node_name[max_node_id] = subject_name
                if not node_name_to_id.has_key(object_name):
                    max_node_id += 1
                    node_name_to_id[object_name] = max_node_id
                    id_to_node_name[max_node_id] = object_name
                edges.add((node_name_to_id[subject_name], node_name_to_id[object_name]))
                count += 1
                if count >= 5000:
                    break

        g = ig.Graph(directed=self.directed)
        g.add_vertices(max_node_id + 1)
        g.add_edges(edges)

        return g, id_to_node_name



    def get_graph_from_SQLDB(self, cutoff=50, year_s=1990, year_e = 1992):
        cnxn = odbc.connect(r'Driver={SQL Server};Server=.\SQLEXPRESS;Database=' + self.dbname + r';Trusted_Connection=yes;')
        #cnxn.autoCommit = True
        cursor = cnxn.cursor()
        if self.dbname == "DBLP4":
            year_start = year_s
            year_end = year_e
            lim_num_docs = cutoff
            params = (year_start, year_end, lim_num_docs)
            q = "Exec Rows_From_Year_Range @year_start = %d, @year_end = %d, @lim_num_docs = %d" % params
            cursor.execute(q)
        else:
            cursor.execute("""SELECT * FROM RDF WHERE [Object] NOT LIKE '%"%' AND [Object] LIKE '%[^0-9]%' AND [Object] NOT LIKE '%Disease_Annotation>%'""")

        node_name_to_id = {}
        id_to_node_name = {}
        edges = set()
        max_node_id = -1
        count = 0
        while 1:
            row = cursor.fetchone()
            if not row:
                break
            subject_name = row.Subject
            predicate_name = row.Predicate
            object_name = row.Object

            #print subject_name+" "+predicate_name+" "+object_name
            if can_skip(subject_name, predicate_name, object_name):
                continue

            if not node_name_to_id.has_key(subject_name):
                max_node_id += 1
                node_name_to_id[subject_name] = max_node_id
                id_to_node_name[max_node_id] = subject_name
            if not node_name_to_id.has_key(object_name):
                max_node_id += 1
                node_name_to_id[object_name] = max_node_id
                id_to_node_name[max_node_id] = object_name
            edges.add((node_name_to_id[subject_name], node_name_to_id[object_name]))
            count += 1
            if self.dbname != "DBLP4" and count >= cutoff:
                break


        cnxn.close()

        g = ig.Graph(directed=self.directed)
        g.add_vertices(max_node_id + 1)
        g.add_edges(edges)

        """
        g.delete_vertices(g.vs.select(_degree=1))

        to_delete = set()
        s = g.vs.find(_degree = 2)
        g.es['has_node'] = [None for _ in range(g.ecount())]
        while s.index not in to_delete:
            to_delete.add(s.index)
            neighbors = g.neighbors(s)
            if not g.are_connected(neighbors[0],neighbors[1]):
                g.add_edge(neighbors[0],neighbors[1])
            edge = g.es.find(_source=neighbors[0],_target=neighbors[1])
            if edge['has_node'] is None:
                edge['has_node'] = []
            edge['has_node'].append(id_to_node_name[s.index])
            s = g.vs.find(_degree=2)
        g.delete_vertices(list(to_delete))
        """

        return g,id_to_node_name

def can_skip(s,p,o):
    if o[0] == '"':
        return True
    return False


