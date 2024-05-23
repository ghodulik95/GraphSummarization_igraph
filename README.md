Code from my Master's thesis, which can be found [here](https://etd.ohiolink.edu/acprod/odb_etd/etd/r/1501/10?clear=10&p10_accession_num=case1482143946391013).

Python based and using igraph, this research loads in test RDF triplestore databases and performs and tests
on different graph summarization algorithms we call Summaries with Supernodes, Superedges, and Corrections (SSSC).

Supernodes are a group of nodes, and superedges are an edge between supernodes, which represent that each node
in the first suprernode are connected to all of the nodes in the second supernode. In triple-stores, such dense
connections can be more common than in other graphs, since a node could be something like a concept that links
to several similar entities. Tracking corrections in superedges allows us to save on some storage, especially
if the vast majority or very few nodes are actually connected by the representation of the superedge.
