import requests
from graphcommons import GraphCommons, Signal
from lxml.html import fromstring
from networkx import DiGraph
import networkx as nx
import matplotlib.pyplot as plt

from requests.packages import urllib3

urllib3.disable_warnings()

fetched_packages = set()


def import_package_dependencies(graph, package_name, max_depth=3, depth=0):
    if package_name in fetched_packages:
        return

    if depth > max_depth:
        return

    fetched_packages.add(package_name)

    url = 'https://www.npmjs.com/package/%s' % package_name
    response = requests.get(url, verify=False)
    doc = fromstring(response.content)

    graph.add_node(package_name, {
        'type': 'PACKAGE'
    })

    for h3 in doc.cssselect('h3'):
        content = h3.text_content()

        if content.strip().startswith('Collaborators') and False:

            for collaborator in h3.getnext().cssselect('a'):
                collaborator_name = collaborator.attrib['title']

                graph.add_node(collaborator_name, {
                    'type': 'CONTRIBUTOR'
                })

                graph.add_edge(collaborator_name, package_name, {
                    'type': 'CONTRIBUTED'
                })

        if content.startswith('Dependencies'):
            for dependency in h3.getnext().cssselect('a'):
                dependency_name = dependency.text_content()

                print('-' * depth * 2, dependency_name)

                graph.add_node(dependency_name, {
                    'type': 'PACKAGE'
                })

                graph.add_edge(package_name, dependency_name, {
                    'type': 'DEPENDS'
                })

                import_package_dependencies(
                    graph,
                    dependency_name,
                    depth=depth + 1
                )


def save_as_csv(name, data, header):
    with open(name + ".csv", 'wb') as csvfile:
        file_str = header[0] + ' ' + header[1] + '\n'
        for tuple in data:
            file_str += str(tuple[0]) + " " + str(tuple[1]) + "\n"
        csvfile.write(file_str)


def analyze_graph(graph):
    print 'Graph analyze:'

    print('DEGREE')
    degree = nx.degree_centrality(graph)
    degree = map(lambda t: (t[0], t[1] * 100), sorted(degree.items(), key=lambda t: t[1], reverse=True)[:10])
    save_as_csv("DEGREE", degree, ("package", "DEGREE"))
    print(degree)

    print('IN_DEGREE')
    in_degree = nx.in_degree_centrality(graph)
    in_degree = map(lambda t: (t[0], t[1] * 100), sorted(in_degree.items(), key=lambda t: t[1], reverse=True)[:10])
    save_as_csv("IN_DEGREE", in_degree, ("package", "IN_DEGREE"))
    print(in_degree)

    print('OUT_DEGREE')
    out_degree = nx.out_degree_centrality(graph)
    out_degree = map(lambda t: (t[0], t[1] * 100), sorted(out_degree.items(), key=lambda t: t[1], reverse=True)[:10])
    save_as_csv("OUT_DEGREE", out_degree, ("package", "OUT_DEGREE"))
    print(out_degree)

    print('BETWEENNESS')
    betweenness = nx.betweenness_centrality(graph)
    betweenness = map(lambda t: (t[0], t[1] * 100), sorted(betweenness.items(), key=lambda t: t[1], reverse=True)[:10])
    save_as_csv("BETWEENNESS", betweenness, ("package", "BETWEENNESS"))
    print(betweenness)

    print('CLOSENESS')
    closeness = nx.closeness_centrality(graph)
    closeness = map(lambda t: (t[0], t[1] * 100), sorted(closeness.items(), key=lambda t: t[1], reverse=True)[:10])
    save_as_csv("CLOSENESS", closeness, ("package", "CLOSENESS"))
    print(closeness)

    print('PAGE RANK')
    pagerank = nx.pagerank(graph)
    pagerank = map(lambda t: (t[0], t[1] * 100), sorted(pagerank.items(), key=lambda t: t[1], reverse=True)[:10])
    save_as_csv("PAGE RANK", pagerank, ("package", "PAGE RANK"))
    print(pagerank)


def load_graph(name):
    return nx.read_graphml(name)


def save_graph(graph, name):
    nx.write_pajek(graph, name + ".net")
    nx.write_graphml(graph, name + ".graphml")
    nx.write_edgelist(graph, name + ".edgelist.txt")


def main(access_token, package_names, max_depth, load_from_file):
    if load_from_file:
        graph = load_graph("npm_dependencies_4_packages_50.graphml")
    else:
        graph = DiGraph()

        for package_name in package_names:
            import_package_dependencies(graph, package_name, max_depth=max_depth)

        save_graph(graph, "npm_dependencies_" + str(max_depth) + "_packages_" + str(len(package_names)))

    graphcommons = GraphCommons(access_token)

    analyze_graph(graph)

    signals = []

    for (node, data) in graph.nodes(data=True):

        if data['type'] == 'PACKAGE':
            reference = "https://www.npmjs.com/package/%s" % node
        else:
            reference = 'https://www.npmjs.com/~%s' % node

        signals.append(Signal(
            action="node_create",
            name=node,
            type=data['type'],
            reference=reference
        ))

    for source, target, data in graph.edges(data=True):
        signals.append(Signal(
            action="edge_create",
            from_name=source,
            from_type=graph.node[source]['type'],
            to_name=target,
            to_type=graph.node[target]['type'],
            name=data['type'],
            weight=1
        ))

    created_graph = graphcommons.new_graph(
        name="Dependency Network of %s" % package_name,
        description="Dependency Network of %s Package" % package_name,
        signals=signals
    )

    print('Created Graph URL:')
    print('https://graphcommons.com/graphs/%s' % created_graph.id)


if __name__ == "__main__":
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("--access_token", dest="access_token",
                      help="API Access to use Graph Commons API. You can get "
                           "this token from your profile page on graphcommons.com")
    parser.add_option("--package_names", dest="package_names",
                      help="NPM package that will be fetched")
    parser.add_option("--depth", dest="depth", type=int,
                      help="Max depth of dependencies")
    options, args = parser.parse_args()
    main(options.access_token, str.split(options.package_names, ','), options.depth, True)
