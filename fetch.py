import requests
from graphcommons import GraphCommons, Signal
from networkx import DiGraph
import networkx as nx
import json

from requests.packages import urllib3

urllib3.disable_warnings()

fetched_packages = set()

def import_package_dependencies(graph, package_name, max_depth=3, depth=0):
    if package_name in fetched_packages:
        return

    if depth > max_depth:
        return


    # test if package_name is a github url
    # Note: Only urls to raw package.json content are currently supported.
    # e.g. https://raw.githubusercontent.com/ipfs/ipfs-webui/main/package.json
    if 'https://raw.githubusercontent.com' in package_name:
      # download the package.json from the github url
      url = package_name
      response = requests.get(url, verify=False)
      pkg_version_info = json.loads(response.text)
      package_name = pkg_version_info['name']
    else:
        url = 'https://registry.npmjs.org/%s' % package_name
        response = requests.get(url, verify=False)
        pkg_registry_info = response.json()

        # Now get the JSON for that version
        url = 'https://registry.npmjs.org/%s/%s' % (package_name, pkg_registry_info['dist-tags']['latest'])
        response = requests.get(url, verify=False)
        # response.content.decode('utf-8')
        pkg_version_info = json.loads(response.text)

    if (options.name_only_id):
      package_identifier = package_name
    else:
      package_identifier = package_name + '@' + pkg_version_info['version']

    if package_identifier in fetched_packages:
      return
    else:
      fetched_packages.add(package_identifier)

    # Convert pkg_version_info to a node in the graph
    graph.add_node(package_identifier.encode('ascii', 'replace'), type='PACKAGE', version=pkg_version_info['version'].encode('ascii', 'replace'))

    # Parse contributors
    if options.add_contributors and 'contributors' in pkg_version_info:
        for contributor in pkg_version_info['contributors']:
            if 'url' in contributor:
              graph.add_node(contributor['url'].encode('ascii', 'replace'), type='CONTRIBUTOR')
              graph.add_edge(package_identifier.encode('ascii', 'replace'), contributor['url'].encode('ascii', 'replace'), type='CONTRIBUTES_TO')
            elif 'email' in contributor:
              graph.add_node(contributor['email'].encode('ascii', 'replace'), type='CONTRIBUTOR')
              graph.add_edge(package_identifier.encode('ascii', 'replace'), contributor['email'].encode('ascii', 'replace'), type='CONTRIBUTES_TO')
            elif 'name' in contributor:
              graph.add_node(contributor['name'].encode('ascii', 'replace'), type='CONTRIBUTOR')
              graph.add_edge(package_identifier.encode('ascii', 'replace'), contributor['name'].encode('ascii', 'replace'), type='CONTRIBUTES_TO')
            else:
              print('Contributor url, email, and name are missing', contributor)

    # Walk the dependencies and add them to the graph
    if 'dependencies' in pkg_version_info:
        for dependency_name in pkg_version_info['dependencies']:
            dependency_identifier = dependency_name + '@' + pkg_version_info['dependencies'][dependency_name]
            graph.add_node(dependency_identifier.encode('ascii', 'replace'), type='PACKAGE')
            graph.add_edge(package_identifier.encode('ascii', 'replace'), dependency_identifier.encode('ascii', 'replace'), type='DEPENDS_ON')
            import_package_dependencies(graph, dependency_name.encode('ascii', 'replace'), max_depth, depth + 1)

def save_as_csv(name, data, header):
    with open(name + ".csv", 'wb') as csvfile:
        file_str = header[0] + ' ' + header[1] + '\n'
        for tuple in data:
            file_str += str(tuple[0]) + " " + str(tuple[1]) + "\n"
        csvfile.write(file_str)


def analyze_graph(graph):
    print('Graph analyze:')

    print('DEGREE')
    degree = nx.degree_centrality(graph)
    degree = [(t[0], t[1] * 100) for t in sorted(list(degree.items()), key=lambda t: t[1], reverse=True)[:10]]
    print(degree)
    save_as_csv("DEGREE", degree, ("package", "DEGREE"))

    print('IN_DEGREE')
    in_degree = nx.in_degree_centrality(graph)
    in_degree = [(t[0], t[1] * 100) for t in sorted(list(in_degree.items()), key=lambda t: t[1], reverse=True)[:10]]
    print(in_degree)
    save_as_csv("IN_DEGREE", in_degree, ("package", "IN_DEGREE"))

    print('OUT_DEGREE')
    out_degree = nx.out_degree_centrality(graph)
    out_degree = [(t[0], t[1] * 100) for t in sorted(list(out_degree.items()), key=lambda t: t[1], reverse=True)[:10]]
    print(out_degree)
    save_as_csv("OUT_DEGREE", out_degree, ("package", "OUT_DEGREE"))

    print('BETWEENNESS')
    betweenness = nx.betweenness_centrality(graph)
    betweenness = [(t[0], t[1] * 100) for t in sorted(list(betweenness.items()), key=lambda t: t[1], reverse=True)[:10]]
    print(betweenness)
    save_as_csv("BETWEENNESS", betweenness, ("package", "BETWEENNESS"))

    print('CLOSENESS')
    closeness = nx.closeness_centrality(graph)
    closeness = [(t[0], t[1] * 100) for t in sorted(list(closeness.items()), key=lambda t: t[1], reverse=True)[:10]]
    print(closeness)
    save_as_csv("CLOSENESS", closeness, ("package", "CLOSENESS"))

    print('PAGE RANK')
    pagerank = nx.pagerank(graph)
    pagerank = [(t[0], t[1] * 100) for t in sorted(list(pagerank.items()), key=lambda t: t[1], reverse=True)[:10]]
    print(pagerank)
    save_as_csv("PAGE RANK", pagerank, ("package", "PAGE RANK"))


def load_graph(name):
    return nx.read_graphml(name)


def save_graph(graph, name):
    nx.write_pajek(graph, name + ".net")
    nx.write_graphml(graph, name + ".graphml")
    nx.write_edgelist(graph, name + ".edgelist.txt")

def get_type_from_data(data):
  if 'type' in data:
    data_type = data['type']
  elif data.get:
    data_type = data.get('type')
  else:
    data_type = 'UNKNOWN'
  return data_type

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
        data_type = get_type_from_data(data)

        if data_type == 'PACKAGE':
            reference = "https://www.npmjs.com/package/%s" % node
        else:
            reference = 'https://www.npmjs.com/~%s' % node

        signals.append(Signal(
            action="node_create",
            name=node,
            type=data_type,
            reference=reference,
        ))

    for source, target, data in graph.edges(data=True):
        signals.append(Signal(
            action="edge_create",
            from_name=source,
            from_type=graph.node[source]['type'],
            to_name=target,
            to_type=graph.node[target]['type'],
            name=get_type_from_data(data),
            weight=1
        ))

    print('options.graph_id', options.graph_id)
    if options.publish:
      if options.graph_id:
        print('Updating graph', options.graph_id)
        graphcommons_result = graphcommons.update_graph(options.graph_id,
            name="Dependency Network of %s" % package_names,
            description="Dependency Network of %s Package" % package_names,
            signals=signals
        )
      else:
        graphcommons_result = graphcommons.new_graph(
            name="Dependency Network of %s" % package_names,
            description="Dependency Network of %s Package" % package_names,
            signals=signals
        )
        print('Created Graph URL:')

      print('https://graphcommons.com/graphs/%s' % graphcommons_result.id)


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
    parser.add_option("--use_cache", dest="use_cache",
                      help="Whether to use cache or not", default=False)
    parser.add_option("--publish", dest="publish",
                      help="Whether to publish a graph on graphcommons", default=False)
    parser.add_option("--add_contributors", dest="add_contributors",
                      help="Whether to add contributors to the graph", default=False)
    parser.add_option("--graph_id", dest="graph_id", help="Graph ID to update")
    parser.add_option("--name_only_id", dest="name_only_id", help="Set the package_identifier to be package_name instead of package_name@version", default=False)
    options, args = parser.parse_args()
    main(options.access_token, str.split(options.package_names, ','), options.depth, options.use_cache)
