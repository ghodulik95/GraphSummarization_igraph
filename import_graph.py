import pyodbc as odbc
import igraph as ig

class Graph_importer:

    def __init__(self, graph_summary_specs):
        self.directed = graph_summary_specs.directed
        self.include_edges = graph_summary_specs.include_edges
        self.include_attributes = graph_summary_specs.include_attributes
        self.edges_annotated = graph_summary_specs.edges_annotated
        self.wa = graph_summary_specs.wa
        self.wc = graph_summary_specs.wc
        self.we = graph_summary_specs.we
        self.dbname = graph_summary_specs.dbname
        self.sql_database = graph_summary_specs.sql_database

    def get_graph_from_RDFDB(self):
        graph = None
        id_to_node_name = None
        if self.sql_database:
            graph, id_to_node_name = self.get_graph_from_SQLDB()
        else:
            graph, id_to_node_name = self.get_graph_from_file()

        if not self.include_attributes:
            attribute_nodes = graph.vs.select(_degree_gt = 75)
            graph.delete_vertices(attribute_nodes)
        return graph, id_to_node_name

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



    def get_graph_from_SQLDB(self):
        cnxn = odbc.connect(r'Driver={SQL Server};Server=.\SQLEXPRESS;Database=' + self.dbname + r';Trusted_Connection=yes;')
        cursor = cnxn.cursor()
        cursor.execute("SELECT * FROM RDF")

        node_name_to_id = {}
        id_to_node_name = {}
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

            if not node_name_to_id.has_key(subject_name):
                max_node_id += 1
                node_name_to_id[subject_name] = max_node_id
                id_to_node_name[max_node_id] = subject_name
            if not node_name_to_id.has_key(object_name):
                max_node_id += 1
                node_name_to_id[object_name] = max_node_id
                id_to_node_name[max_node_id] = object_name
            edges.add((node_name_to_id[subject_name], node_name_to_id[object_name]))
            if count > 5000:
                break


        cnxn.close()

        g = ig.Graph(directed=self.directed)
        g.add_vertices(max_node_id + 1)
        g.add_edges(edges)
        return g,id_to_node_name

def can_skip(s,p,o):
    #if '#' in s:
    #    return True
    return False


