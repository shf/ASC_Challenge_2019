# This code converts the .unv format to .xml format
import collections

import numpy as np



# Reading UNV file
UNVFile = open("./MeshImporter/MeshUNV.unv", "r").readlines()
flag = None
nodes = {}
connectivit = {}
TriangleElement = False
for line in UNVFile:
    temp = line.split()
    if "-1" in temp:
        flag = None
    if flag == "Nodes":
        if len(temp) == 4:
            NodeID = temp[0]
        if len(temp) == 3:
            nodes[NodeID] = temp
    if flag == "Elements":
        if len(temp) == 6:
            if temp[5] == "3":
                TriangleElement = True
                CellID = temp[0]
        if len(temp) == 3 and TriangleElement:
            connectivit[CellID] = temp
            TriangleElement = False
    if "2411" in line and len(temp) == 1:
        flag = "Nodes"
    if "2412" in line and len(temp) == 1:
        flag = "Elements"
SortedConnectivity = collections.OrderedDict(sorted(connectivit.items()))

# writing xml file
XMLFile = open("./MeshImporter/mesh.xml", "w")
XMLFile.write("<dolfin xmlns:dolfin=\"https://fenicsproject.org/\">\n")
XMLFile.write("  <mesh celltype=\"triangle\" dim=\"3\">\n")
XMLFile.write("    <vertices size=\"{}\">\n".format(len(nodes)+1))
for key, value in nodes.items():
    XMLFile.write("      <vertex index=\"{}\" x=\"{}\" y=\"{}\" z=\"{}\"/>\n".format(
        key, value[0], value[1], value[2]))
XMLFile.write("    </vertices>\n")
XMLFile.write("    <cells size=\"{}\">\n".format(int(min(SortedConnectivity.keys()))+len(SortedConnectivity)))
for key, value in SortedConnectivity.items():
    XMLFile.write("      <triangle index=\"{}\" v0=\"{}\" v1=\"{}\" v2=\"{}\"/>\n".format(
        key, value[0], value[1], value[2]))
XMLFile.write("    </cells>\n")
XMLFile.write("  </mesh>\n")
XMLFile.write("</dolfin>\n")
XMLFile.close()
