import import_graph
from graph_summary_randomized import Graph_Summary_Random, visualize
from graph_summary_densesubgraphs import Graph_Summary_Dense
from graph_summary_modules import Graph_Summary_Module
import random

def get_avg_support(g):
    support = []

    for edge in g.s.es:
        u = edge.source
        v = edge.target
        support.append(g.get_support_of_edge_between_supernodes(u,v))

    return (sum(support) / float(len(support)))

def get_prob_connected(g):
    num_connected_with_superedge = 0
    num_connected_with_correction = 0
    num_tries = 3000
    num_not_connected = 0
    for i in range(num_tries):
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
            num_not_connected += 1


    return float(num_connected_with_superedge)/num_tries, float(num_connected_with_correction) / num_tries, float(num_not_connected) / num_tries

def get_data(graph,has_cutoff, display_req=None, display_comp=None):
    """
    :type graph: Graph_Summary_Random
    :return:
    """
    data = {}
    data['dbname'] = graph.dbname
    data['original_num_vertices'] = graph.g.vcount()
    data['summary_num_vertices'] = graph.s.vcount()
    data['originial_num_edges'] = graph.g.ecount()
    data['summary_num_edges'] = graph.s.ecount()
    data['num_corrections'] = len(graph.additions) + len(graph.subtractions)
    data['num_additions'] = len(graph.additions)
    data['num_subtractions'] = len(graph.subtractions)
    data['summary_cost'] = graph.get_cost()
    data['compression_ratio'] = float(data['summary_cost']) / data['originial_num_edges']
    if has_cutoff:
        data['cutoff'] = graph.cutoff
    else:
        data['cutoff'] = "None"

    if display_req is None:
        data['display_req'] = graph.display_req
    else:
        data['display_req'] = display_req

    if display_comp is None:
        data['display_comp'] = graph.display_comp
    else:
        data['display_comp'] = display_comp

    data['step'] = graph.step
    data['num_allowable_skips'] = graph.num_allowable_skips
    perc_connected_superedge, perc_connected_correction, perc_not_connected = get_prob_connected(graph)
    data['perc_connected_superedge'] = perc_connected_superedge
    data['perc_connected_correction'] = perc_connected_correction
    data['perc_not_connected'] = perc_not_connected
    data['avg_support'] = get_avg_support(graph)
    data['runtime'] = graph.runtime
    return data




def get_data_row_CSV(graph,has_cutoff,col_order, display_req=None, display_comp=None):
    data = get_data(graph,has_cutoff,display_req,display_comp)
    to_return=''
    first = True
    for col in col_order:
        if not first:
            to_return = to_return + ","
        d = data[col]
        if d is None:
            d = '"None"'
        to_return = to_return + str(d)
        first = False
    return to_return

def get_CSV_header(col_order):
    header = ''
    first = True
    for h in col_order:
        if not first:
            header = header + ","
        header = header + '"'+h+'"'
        first = False
    return header

if __name__ == "__main__":
    col_order = ['dbname','original_num_vertices','summary_num_vertices','originial_num_edges','summary_num_edges','num_corrections',
                 'num_additions','num_subtractions','summary_cost', 'compression_ratio','cutoff','step','num_allowable_skips','display_req','display_comp','perc_connected_superedge','perc_connected_correction',
                 'perc_not_connected','avg_support','runtime']
    csv_header = get_CSV_header(col_order)
    numdocs = [[5000, None, None], [10000, None, None]]

    dense_f = open("Dense_datatest.csv", "a")
    dense_f.write(csv_header+"\n")
    mod_f = open("Mod_datatest.csv", "a")
    mod_f.write(csv_header+"\n")

    for num in numdocs:
        cutoff = num[0]
        year_start = num[1]
        year_end = num[2]

        graph_importer = import_graph.Graph_importer(None,"uniprotTest")
        g, original_id_to_name = graph_importer.get_graph_from_RDFDB(cutoff,year_start,year_end)
        del graph_importer


        sum_mod = Graph_Summary_Module(source_graph=g,original_id_to_node_name=original_id_to_name, dbname="uniprot_test")
        #visualize("throaway", sum_mod)
        mod_f.write(get_data_row_CSV(sum_mod, False, col_order)+"\n")
        mod_f.flush()
        for _ in range(5):

            sum_dense = Graph_Summary_Dense(source_graph=g, original_id_to_node_name=original_id_to_name, dbname="uniprot_test")
            #visualize("throaway", sum_dense)
            dense_f.write(get_data_row_CSV(sum_dense, False, col_order)+"\n")
            dense_f.flush()


        print "Finished "

    dense_f.close()
    mod_f.close()

    rand_f = open("Random_datatest.csv", "a")
    rand_f.write(csv_header+"\n")

    for num in numdocs:
        cutoff = num[0]
        year_start = num[1]
        year_end = num[2]
        graph_importer = import_graph.Graph_importer(None,"uniprotTest")
        g, original_id_to_name = graph_importer.get_graph_from_RDFDB(cutoff,year_start,year_end)
        del graph_importer
        for _ in range(1):
            """
            sum_rand = Graph_Summary_Random(source_graph=g,original_id_to_node_name=original_id_to_name,cutoff=0.5,display_req=0.5,display_comp="gr",step=0.01, num_allowable_skips=10)
            rand_f.write(get_data_row_CSV(sum_rand, True, col_order)+"\n")
            sum_rand.put_edges_on_summary(0.5,"gre")
            rand_f.write(get_data_row_CSV(sum_rand,True,col_order,display_comp="gre")+"\n")
            sum_rand.put_edges_on_summary(0.3,"gre")
            rand_f.write(get_data_row_CSV(sum_rand,True, col_order,0.3,"gre")+"\n")
            rand_f.flush()

            print "finished1"
            sum_rand = Graph_Summary_Random(source_graph=g,original_id_to_node_name=original_id_to_name,cutoff=0.3,display_req=0.5,display_comp="gr",step=0, num_allowable_skips=1000)
            rand_f.write(get_data_row_CSV(sum_rand, True, col_order)+"\n")
            rand_f.flush()
            print "finished2"
            sum_rand = Graph_Summary_Random(source_graph=g,original_id_to_node_name=original_id_to_name,cutoff=0.2,display_req=0.5,display_comp="gr",step=0, num_allowable_skips=1000)
            rand_f.write(get_data_row_CSV(sum_rand, True, col_order)+"\n")
            rand_f.flush()
            print "finished3"
            """
            sum_rand = Graph_Summary_Random(source_graph=g,original_id_to_node_name=original_id_to_name,cutoff=0,display_req=0.5,display_comp="gr",step=0, num_allowable_skips=1000, dbname="uniprot_test")
            rand_f.write(get_data_row_CSV(sum_rand, True, col_order)+"\n")
            rand_f.flush()

        print "Finished "

    rand_f.close()



