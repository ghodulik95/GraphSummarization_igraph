from pymining import itemmining
import igraph as ig
import graph_summary_randomized as gs
from sortedcontainers import SortedListWithKey

class Graph_Heuristic:
    def __init__(self,g):
        self.g = g # type: ig.Graph
        self.relim_input = self.get_relim_input()
        self.best_shared_neighbors = self.get_best_shared_neighbor_order()
        self.size_up_graph()

    def get_relim_input(self):
        list_of_neighbors = self.g.neighborhood(vertices=self.g.vs,order=1)
        return itemmining.get_relim_input(list_of_neighbors)

    def get_frequent_itemsets_with_support(self,support=2):
        return itemmining.relim(self.relim_input,min_support=support)

    def get_best_shared_neighbor_order(self):
        itemsets = self.get_frequent_itemsets_with_support()
        itemsets_sorted = SortedListWithKey(itemsets.key     s(),key=lambda x: -len(x)*itemsets[x])
        return itemsets_sorted

    def size_up_graph(self):
        for i in self.best_shared_neighbors:
            if len(i) > 2:
                for j in i:
                    self.g.vs[j]['size'] += 30
                break

if __name__ == "__main__":
    dbname = "DBLP4"
    g = gs.Graph_Summary(False,True,False,False,dbname)
    i = 0
    for n in g.g.vs:
        n["label"] = "%d,%s" % (i,+n["label"])
        i += 1

    layout = g.g.layout("kk")
    visual_style = {}
    visual_style["layout"] = layout
    visual_style["bbox"] = (1650, 1650)
    ig.plot(g.g, **visual_style).save("graph_with_ids_for_itemsets.png")
    gh = Graph_Heuristic(g.g)
    itemsets = gh.best_shared_neighbors
    print itemsets